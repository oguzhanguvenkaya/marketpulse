import re
import asyncio
import time
import logging
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)

_stop_signals: dict[str, bool] = {}


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


class TranscriptService:
    MAX_CONCURRENT = 10

    def fetch_transcript(self, video_url: str) -> dict:
        video_id = extract_video_id(video_url)
        if not video_id:
            return {'video_url': video_url, 'error': f'Could not extract video ID from URL: {video_url}'}

        try:
            ytt_api = YouTubeTranscriptApi()

            transcript = None
            try:
                transcript_list = ytt_api.list(video_id)
                available = list(transcript_list)
                if available:
                    manual = [t for t in available if not t.is_generated]
                    chosen = manual[0] if manual else available[0]
                    transcript = ytt_api.fetch(video_id, languages=[chosen.language_code])
            except Exception:
                pass

            if transcript is None:
                transcript = ytt_api.fetch(video_id)

            full_text = ' '.join(snippet.text for snippet in transcript.snippets)

            snippets_data = [
                {
                    'text': snippet.text,
                    'start': snippet.start,
                    'duration': snippet.duration,
                }
                for snippet in transcript.snippets
            ]

            return {
                'video_url': video_url,
                'video_id': video_id,
                'language': transcript.language,
                'language_code': transcript.language_code,
                'is_generated': transcript.is_generated,
                'transcript_text': full_text,
                'snippets': snippets_data,
                'snippet_count': len(snippets_data),
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[TRANSCRIPT] Error fetching transcript for {video_id}: {error_msg}")
            return {'video_url': video_url, 'video_id': video_id, 'error': error_msg}

    async def fetch_transcripts_batch(self, result_ids_urls: list[tuple], db_factory, job_id: str = None):
        total = len(result_ids_urls)
        completed_count = 0
        failed_count = 0
        batch_start = time.time()
        stopped = False
        jid = (job_id or '?')[:8]

        logger.info(f"[TRANSCRIPT {jid}] Starting batch: {total} videos, concurrency={self.MAX_CONCURRENT}")

        queue: asyncio.Queue = asyncio.Queue()
        for item in result_ids_urls:
            await queue.put(item)

        write_lock = asyncio.Lock()

        async def worker():
            nonlocal completed_count, failed_count, stopped
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

                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.fetch_transcript, video_url
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
                logger.info(
                    f"[TRANSCRIPT {jid}] [{done}/{total}] "
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
        logger.info(
            f"[TRANSCRIPT {jid}] Batch finished in {batch_elapsed}s — "
            f"OK: {completed_count}, FAIL: {failed_count}, SKIPPED: {skipped_count}, TOTAL: {total}"
            + (" (STOPPED by user)" if stopped else "")
        )

        if job_id:
            clear_stop_signal(job_id)

        return {"completed": completed_count, "failed": failed_count, "skipped": skipped_count, "stopped": stopped}
