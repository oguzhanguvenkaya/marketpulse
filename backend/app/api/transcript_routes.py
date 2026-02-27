import csv
import io
import json
import uuid as uuid_mod
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, BackgroundTasks, UploadFile, File, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db, SessionLocal
from app.db.models import TranscriptJob, TranscriptResult, User
from app.core.auth import get_current_user
from app.core.url_validator import validate_url_safe

router = APIRouter(
    prefix="/api/transcripts",
    tags=["Video Transcripts"],
    dependencies=[Depends(get_current_user)],
)


class SingleVideoRequest(BaseModel):
    video_url: str
    product_name: Optional[str] = None
    barcode: Optional[str] = None


class BulkVideoRequest(BaseModel):
    videos: List[SingleVideoRequest]


@router.post("/fetch")
async def fetch_single_transcript(req: SingleVideoRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    is_safe, error_msg = validate_url_safe(req.video_url)
    if not is_safe:
        raise HTTPException(status_code=400, detail=error_msg)

    job = TranscriptJob(total_videos=1, status="running", user_id=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)

    result = TranscriptResult(
        transcript_job_id=job.id,
        video_url=req.video_url,
        product_name=req.product_name,
        barcode=req.barcode,
        status="pending"
    )
    db.add(result)
    db.commit()

    background_tasks.add_task(run_transcript_job, str(job.id))

    return {"job_id": str(job.id), "status": "running", "total_videos": 1}


@router.post("/fetch-bulk")
async def fetch_bulk_transcripts(req: BulkVideoRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for v in req.videos:
        is_safe, error_msg = validate_url_safe(v.video_url)
        if not is_safe:
            raise HTTPException(status_code=400, detail=f"URL guvenli degil ({v.video_url}): {error_msg}")

    job = TranscriptJob(total_videos=len(req.videos), status="running", user_id=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)

    for v in req.videos:
        result = TranscriptResult(
            transcript_job_id=job.id,
            video_url=v.video_url,
            product_name=v.product_name,
            barcode=v.barcode,
            status="pending"
        )
        db.add(result)
    db.commit()

    background_tasks.add_task(run_transcript_job, str(job.id))

    return {"job_id": str(job.id), "status": "running", "total_videos": len(req.videos)}


def _detect_csv_delimiter(text: str) -> str:
    first_lines = text.split('\n', 3)[:3]
    sample = '\n'.join(first_lines)
    semicolons = sample.count(';')
    commas = sample.count(',')
    tabs = sample.count('\t')
    counts = {';': semicolons, ',': commas, '\t': tabs}
    return max(counts, key=counts.get) if max(counts.values()) > 0 else ','


def _extract_video_urls_from_cell(cell: str) -> list[str]:
    cell = cell.strip()
    if not cell:
        return []
    if 'youtube.com' in cell or 'youtu.be' in cell:
        return [cell]
    return []


@router.post("/fetch-csv")
async def fetch_csv_transcripts(file: UploadFile = File(...), background_tasks: BackgroundTasks = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = await file.read()
    text = content.decode('utf-8-sig')

    delimiter = _detect_csv_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, None)
    if not header:
        raise HTTPException(status_code=400, detail="Empty CSV file")

    video_url_columns = []
    name_col = None
    barcode_col = None
    for i, h in enumerate(header):
        h_lower = h.strip().lower()
        if 'video' in h_lower and ('url' in h_lower or 'link' in h_lower):
            video_url_columns.append(i)
        if h_lower in ['product name', 'name', 'ürün adı', 'product_name', 'ürün', 'urun']:
            name_col = i
        if h_lower in ['barcode', 'barkod']:
            barcode_col = i

    if not video_url_columns:
        for i, h in enumerate(header):
            h_lower = h.strip().lower()
            if 'video' in h_lower:
                video_url_columns.append(i)

    if not video_url_columns:
        raise HTTPException(
            status_code=400,
            detail="No video URL columns found in CSV. Expected columns with 'video' in the name (e.g., Video_URL, Video_URL1). "
                   "Header columns detected: " + ", ".join(h.strip() for h in header)
        )

    videos_to_fetch = []
    skipped_rows = 0
    for row in reader:
        product_name = row[name_col].strip() if name_col is not None and name_col < len(row) else None
        barcode = row[barcode_col].strip() if barcode_col is not None and barcode_col < len(row) else None

        row_has_video = False
        for col_idx in video_url_columns:
            if col_idx < len(row):
                urls = _extract_video_urls_from_cell(row[col_idx])
                for url in urls:
                    row_has_video = True
                    videos_to_fetch.append({
                        'video_url': url,
                        'product_name': product_name,
                        'barcode': barcode
                    })
        if not row_has_video and (product_name or barcode):
            skipped_rows += 1

    if not videos_to_fetch:
        raise HTTPException(status_code=400, detail="No valid YouTube video URLs found in CSV")

    unsafe_urls = []
    for v in videos_to_fetch:
        is_safe, error_msg = validate_url_safe(v['video_url'])
        if not is_safe:
            unsafe_urls.append(f"{v['video_url']}: {error_msg}")
    if unsafe_urls:
        raise HTTPException(status_code=400, detail=f"Guvenli olmayan URL'ler tespit edildi: {'; '.join(unsafe_urls)}")

    seen = set()
    unique_videos = []
    for v in videos_to_fetch:
        if v['video_url'] not in seen:
            seen.add(v['video_url'])
            unique_videos.append(v)
    duplicates_removed = len(videos_to_fetch) - len(unique_videos)
    videos_to_fetch = unique_videos

    job = TranscriptJob(total_videos=len(videos_to_fetch), status="running", user_id=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)

    for v in videos_to_fetch:
        result = TranscriptResult(
            transcript_job_id=job.id,
            video_url=v['video_url'],
            product_name=v.get('product_name'),
            barcode=v.get('barcode'),
            status="pending"
        )
        db.add(result)
    db.commit()

    background_tasks.add_task(run_transcript_job, str(job.id))

    resp = {"job_id": str(job.id), "status": "running", "total_videos": len(videos_to_fetch)}
    if skipped_rows > 0:
        resp["skipped_rows"] = skipped_rows
        resp["message"] = f"{skipped_rows} row(s) skipped (no video URLs)"
    if duplicates_removed > 0:
        resp["duplicates_removed"] = duplicates_removed
    return resp


@router.get("/jobs")
async def get_transcript_jobs(limit: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(TranscriptJob).filter(TranscriptJob.user_id == user.id).order_by(TranscriptJob.created_at.desc()).limit(limit).all()
    return [{
        "id": str(j.id),
        "status": j.status,
        "total_videos": j.total_videos,
        "completed_videos": j.completed_videos,
        "failed_videos": j.failed_videos,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        "error_message": j.error_message
    } for j in jobs]


@router.get("/jobs/{job_id}")
async def get_transcript_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(TranscriptJob).filter(TranscriptJob.id == uuid_mod.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = db.query(TranscriptResult).filter(TranscriptResult.transcript_job_id == job.id).all()

    return {
        "id": str(job.id),
        "status": job.status,
        "total_videos": job.total_videos,
        "completed_videos": job.completed_videos,
        "failed_videos": job.failed_videos,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "results": [{
            "id": r.id,
            "video_url": r.video_url,
            "product_name": r.product_name,
            "barcode": r.barcode,
            "status": r.status,
            "language": r.language,
            "language_code": r.language_code,
            "is_generated": r.is_generated,
            "transcript_text": r.transcript_text,
            "snippet_count": len(r.transcript_snippets) if r.transcript_snippets else 0,
            "error_message": r.error_message
        } for r in results]
    }


@router.get("/jobs/{job_id}/download")
async def download_transcript_results(job_id: str, db: Session = Depends(get_db)):
    job = db.query(TranscriptJob).filter(TranscriptJob.id == uuid_mod.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = db.query(TranscriptResult).filter(
        TranscriptResult.transcript_job_id == job.id,
        TranscriptResult.status == "completed"
    ).all()

    export_data = []
    for r in results:
        item = {
            "video_url": r.video_url,
            "product_name": r.product_name,
            "barcode": r.barcode,
            "language": r.language,
            "language_code": r.language_code,
            "is_generated": r.is_generated,
            "transcript_text": r.transcript_text,
            "snippets": r.transcript_snippets,
        }
        export_data.append(item)

    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=transcripts_{job_id[:8]}.json"
        }
    )


@router.delete("/jobs/{job_id}")
async def delete_transcript_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(TranscriptJob).filter(TranscriptJob.id == uuid_mod.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    return {"success": True, "message": "Job deleted"}


@router.post("/jobs/{job_id}/stop")
async def stop_transcript_job(job_id: str, db: Session = Depends(get_db)):
    from app.services.transcript_service import request_stop

    job = db.query(TranscriptJob).filter(TranscriptJob.id == uuid_mod.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "running":
        raise HTTPException(status_code=400, detail="Job is not running")

    request_stop(job_id)
    return {"success": True, "message": "Stop signal sent"}


async def run_transcript_job(job_id: str):
    import logging
    from app.services.transcript_service import TranscriptService

    logger = logging.getLogger(__name__)

    db = SessionLocal()
    try:
        job = db.query(TranscriptJob).filter(TranscriptJob.id == uuid_mod.UUID(job_id)).first()
        if not job:
            logger.error(f"[TRANSCRIPT {job_id[:8]}] Job not found in DB")
            return

        job.status = "running"
        db.commit()
        logger.info(f"[TRANSCRIPT {job_id[:8]}] Job started — {job.total_videos} videos to process")

        results = db.query(TranscriptResult).filter(
            TranscriptResult.transcript_job_id == job.id,
            TranscriptResult.status == "pending"
        ).all()

        result_ids_urls = [(r.id, r.video_url) for r in results]

        service = TranscriptService()
        batch_result = await service.fetch_transcripts_batch(result_ids_urls, SessionLocal, job_id=job_id)

        completed = db.query(TranscriptResult).filter(
            TranscriptResult.transcript_job_id == job.id,
            TranscriptResult.status == "completed"
        ).count()
        failed = db.query(TranscriptResult).filter(
            TranscriptResult.transcript_job_id == job.id,
            TranscriptResult.status == "failed"
        ).count()

        job.completed_videos = completed
        job.failed_videos = failed

        if batch_result and batch_result.get("stopped"):
            job.status = "stopped"
            logger.info(f"[TRANSCRIPT {job_id[:8]}] Job stopped by user — OK: {completed}, FAIL: {failed}")
        else:
            job.status = "completed"
            logger.info(f"[TRANSCRIPT {job_id[:8]}] Job completed — OK: {completed}, FAIL: {failed}")

        job.completed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.error(f"[TRANSCRIPT {job_id[:8]}] Job failed with exception: {e}")
        try:
            job.status = "failed"
            job.error_message = str(e)
            completed = db.query(TranscriptResult).filter(
                TranscriptResult.transcript_job_id == job.id,
                TranscriptResult.status == "completed"
            ).count()
            failed = db.query(TranscriptResult).filter(
                TranscriptResult.transcript_job_id == job.id,
                TranscriptResult.status == "failed"
            ).count()
            job.completed_videos = completed
            job.failed_videos = failed
            job.completed_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.critical(f"[TRANSCRIPT {job_id[:8]}] Failed to mark job as failed: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        db.close()
