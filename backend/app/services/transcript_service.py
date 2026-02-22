import re
import asyncio
import time
import logging
import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from youtube_transcript_api._errors import RequestBlocked, IpBlocked

logger = logging.getLogger(__name__)

_stop_signals: dict[str, bool] = {}

IP_BLOCK_ERRORS = (RequestBlocked, IpBlocked)
IP_BLOCK_THRESHOLD = 3


def request_stop(job_id: str):
    _stop_signals[job_id] = True
    logger.info(f"[TRANSCRIPT {job_id[:8]}] Stop signal received")


def is_stop_requested(job_id: str) -> bool:
    return _stop_signals.get(job_id, False)


def clear_stop_signal(job_id: str):
    _stop_signals.pop(job_id, None)


def extract_video_id(url: str) -> str | None:
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _build_scraperapi_proxy_url():
    api_key = os.getenv("SCRAPPER_API", "")
    if not api_key:
        return None
    return f"http://scraperapi:{api_key}@proxy-server.scraperapi.com:8001"


def _create_proxy_api(proxy_url: str) -> YouTubeTranscriptApi:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    from requests import Session
    proxy_config = GenericProxyConfig(
        http_url=proxy_url,
        https_url=proxy_url,
    )
    session = Session()
    session.verify = False
    return YouTubeTranscriptApi(proxy_config=proxy_config, http_client=session)


def _pick_best_transcript(available: list, video_id: str):
    auto_generated = [t for t in available if t.is_generated]
    manual = [t for t in available if not t.is_generated]

    langs_info = ', '.join(f"{t.language_code}({'m' if not t.is_generated else 'a'})" for t in available)
    logger.info(f"[TRANSCRIPT] {video_id}: available=[{langs_info}]")

    original_lang = None
    if auto_generated:
        original_lang = auto_generated[0].language_code

    if original_lang:
        manual_orig = [t for t in manual if t.language_code == original_lang]
        if manual_orig:
            return manual_orig[0]
        auto_orig = [t for t in auto_generated if t.language_code == original_lang]
        if auto_orig:
            return auto_orig[0]

    for lang_prefix in ['en', 'tr']:
        manual_match = [t for t in manual if t.language_code.startswith(lang_prefix)]
        if manual_match:
            return manual_match[0]
        auto_match = [t for t in auto_generated if t.language_code.startswith(lang_prefix)]
        if auto_match:
            return auto_match[0]

    if manual:
        return manual[0]
    if auto_generated:
        return auto_generated[0]
    return available[0]


def _fetch_with_api(ytt_api: YouTubeTranscriptApi, video_id: str):
    transcript = None
    try:
        transcript_list = ytt_api.list(video_id)
        available = list(transcript_list)
        if available:
            chosen = _pick_best_transcript(available, video_id)
            transcript = ytt_api.fetch(video_id, languages=[chosen.language_code])
            logger.info(f"[TRANSCRIPT] {video_id}: selected '{chosen.language}' ({chosen.language_code}), generated={chosen.is_generated}")
    except IP_BLOCK_ERRORS:
        raise
    except Exception as e:
        logger.warning(f"[TRANSCRIPT] {video_id}: list/select failed ({e}), falling back to default fetch")

    if transcript is None:
        transcript = ytt_api.fetch(video_id)

    return transcript


class TranscriptService:
    MAX_CONCURRENT = 40

    def fetch_transcript(self, video_url: str, force_proxy: bool = False) -> dict:
        video_id = extract_video_id(video_url)
        if not video_id:
            return {'video_url': video_url, 'error': f'Could not extract video ID from URL: {video_url}'}

        proxy_url = _build_scraperapi_proxy_url()

        ip_was_blocked = False

        if not force_proxy:
            try:
                ytt_direct = YouTubeTranscriptApi()
                transcript = _fetch_with_api(ytt_direct, video_id)
                return self._format_result(video_url, video_id, transcript, proxy_used=None)
            except IP_BLOCK_ERRORS:
                ip_was_blocked = True
                logger.warning(f"[TRANSCRIPT] IP blocked for {video_id}, retrying with ScraperAPI proxy...")
                if not proxy_url:
                    return {'video_url': video_url, 'video_id': video_id, 'error': 'IP blocked and no proxy configured', 'ip_blocked': True}
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[TRANSCRIPT] Error fetching transcript for {video_id}: {error_msg}")
                return {'video_url': video_url, 'video_id': video_id, 'error': error_msg}
        else:
            logger.info(f"[TRANSCRIPT] Using ScraperAPI proxy directly for {video_id} (proxy mode active)")

        if not proxy_url:
            return {'video_url': video_url, 'video_id': video_id, 'error': 'ScraperAPI key not configured'}

        try:
            ytt_proxy = _create_proxy_api(proxy_url)
            transcript = _fetch_with_api(ytt_proxy, video_id)
            result = self._format_result(video_url, video_id, transcript, proxy_used='scraperapi')
            if ip_was_blocked:
                result['ip_blocked'] = True
            return result
        except Exception as proxy_err:
            error_msg = str(proxy_err)
            logger.error(f"[TRANSCRIPT] ScraperAPI proxy failed for {video_id}: {error_msg}")
            return {'video_url': video_url, 'video_id': video_id, 'error': f'Failed with proxy: {error_msg}', 'ip_blocked': ip_was_blocked}

    def _format_result(self, video_url: str, video_id: str, transcript, proxy_used: str | None) -> dict:
        full_text = ' '.join(snippet.text for snippet in transcript.snippets)
        snippets_data = [
            {
                'text': snippet.text,
                'start': snippet.start,
                'duration': snippet.duration,
            }
            for snippet in transcript.snippets
        ]

        result = {
            'video_url': video_url,
            'video_id': video_id,
            'language': transcript.language,
            'language_code': transcript.language_code,
            'is_generated': transcript.is_generated,
            'transcript_text': full_text,
            'snippets': snippets_data,
            'snippet_count': len(snippets_data),
        }
        if proxy_used:
            logger.info(f"[TRANSCRIPT] Successfully fetched {video_id} via {proxy_used} proxy")
        return result

    async def fetch_transcripts_batch(self, result_ids_urls: list[tuple], db_factory, job_id: str = None):
        total = len(result_ids_urls)
        completed_count = 0
        failed_count = 0
        ip_block_count = 0
        proxy_mode_event = asyncio.Event()
        batch_start = time.time()
        stopped = False
        jid = (job_id or '?')[:8]

        logger.info(f"[TRANSCRIPT {jid}] Starting batch: {total} videos, concurrency={self.MAX_CONCURRENT}")

        queue: asyncio.Queue = asyncio.Queue()
        for item in result_ids_urls:
            await queue.put(item)

        write_lock = asyncio.Lock()

        async def worker():
            nonlocal completed_count, failed_count, stopped, ip_block_count
            while True:
                if job_id and is_stop_requested(job_id):
                    stopped = True
                    return

                try:
                    result_id, video_url = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return

                url_start = time.time()
                status = 'failed'
                language = None
                language_code = None
                is_generated = None
                transcript_text = None
                transcript_snippets = None
                error_message = None

                use_proxy = proxy_mode_event.is_set()

                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.fetch_transcript, video_url, use_proxy
                    )

                    if result.get('ip_blocked') and not proxy_mode_event.is_set():
                        ip_block_count += 1
                        if ip_block_count >= IP_BLOCK_THRESHOLD:
                            proxy_mode_event.set()
                            logger.warning(
                                f"[TRANSCRIPT {jid}] IP blocked {ip_block_count} times, "
                                f"switching ALL remaining videos to ScraperAPI proxy"
                            )

                    if 'error' not in result:
                        status = 'completed'
                        language = result.get('language')
                        language_code = result.get('language_code')
                        is_generated = result.get('is_generated')
                        transcript_text = result.get('transcript_text')
                        transcript_snippets = result.get('snippets')
                        completed_count += 1
                    else:
                        error_message = result.get('error')
                        failed_count += 1
                except Exception as e:
                    error_message = str(e)
                    failed_count += 1
                    logger.error(f"[TRANSCRIPT {jid}] Exception for {video_url[:60]}: {e}")

                url_elapsed = round(time.time() - url_start, 1)
                done = completed_count + failed_count
                proxy_label = " [PROXY]" if use_proxy else ""
                logger.info(
                    f"[TRANSCRIPT {jid}] [{done}/{total}]{proxy_label} "
                    f"{'OK' if status == 'completed' else 'FAIL'} "
                    f"{video_url[:70]} — {url_elapsed}s"
                )

                async with write_lock:
                    db = db_factory()
                    try:
                        from app.db.models import TranscriptResult, TranscriptJob
                        import uuid as uuid_mod
                        db.query(TranscriptResult).filter(TranscriptResult.id == result_id).update({
                            'status': status,
                            'language': language,
                            'language_code': language_code,
                            'is_generated': is_generated,
                            'transcript_text': transcript_text,
                            'transcript_snippets': transcript_snippets,
                            'error_message': error_message,
                        })
                        if job_id:
                            db.query(TranscriptJob).filter(TranscriptJob.id == uuid_mod.UUID(job_id)).update({
                                'completed_videos': completed_count,
                                'failed_videos': failed_count,
                            })
                        db.commit()
                    except Exception as e:
                        logger.error(f"[TRANSCRIPT {jid}] DB write error for result {result_id}: {e}")
                        db.rollback()
                    finally:
                        db.close()

        workers = [asyncio.create_task(worker()) for _ in range(self.MAX_CONCURRENT)]
        await asyncio.gather(*workers, return_exceptions=True)

        if job_id and is_stop_requested(job_id):
            stopped = True

        skipped_count = 0
        if stopped:
            db = db_factory()
            try:
                from app.db.models import TranscriptResult
                import uuid as uuid_mod
                skipped_count = db.query(TranscriptResult).filter(
                    TranscriptResult.transcript_job_id == uuid_mod.UUID(job_id),
                    TranscriptResult.status == 'pending'
                ).update({'status': 'skipped'})
                db.commit()
                logger.info(f"[TRANSCRIPT {jid}] Marked {skipped_count} remaining videos as skipped")
            except Exception as e:
                logger.error(f"[TRANSCRIPT {jid}] Error marking skipped: {e}")
                db.rollback()
            finally:
                db.close()

        batch_elapsed = round(time.time() - batch_start, 1)
        proxy_info = f", proxy_mode={'ON' if proxy_mode_event.is_set() else 'OFF'} (blocks: {ip_block_count})"
        logger.info(
            f"[TRANSCRIPT {jid}] Batch finished in {batch_elapsed}s — "
            f"OK: {completed_count}, FAIL: {failed_count}, SKIPPED: {skipped_count}, TOTAL: {total}"
            f"{proxy_info}"
            + (" (STOPPED by user)" if stopped else "")
        )

        if job_id:
            clear_stop_signal(job_id)

        return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count, "stopped": stopped}
