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
from app.db.models import ScrapeJob, ScrapeResult

router = APIRouter(prefix="/api/url-scraper", tags=["URL Scraper"])


class SingleUrlRequest(BaseModel):
    url: str
    product_name: Optional[str] = None
    barcode: Optional[str] = None


class BulkUrlRequest(BaseModel):
    urls: List[SingleUrlRequest]


@router.post("/scrape")
async def scrape_single_url(req: SingleUrlRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = ScrapeJob(total_urls=1, status="running")
    db.add(job)
    db.commit()
    db.refresh(job)

    result = ScrapeResult(
        scrape_job_id=job.id,
        url=req.url,
        product_name=req.product_name,
        barcode=req.barcode,
        status="pending"
    )
    db.add(result)
    db.commit()

    background_tasks.add_task(run_scrape_job, str(job.id))

    return {"job_id": str(job.id), "status": "running", "total_urls": 1}


@router.post("/scrape-bulk")
async def scrape_bulk_urls(req: BulkUrlRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = ScrapeJob(total_urls=len(req.urls), status="running")
    db.add(job)
    db.commit()
    db.refresh(job)

    for u in req.urls:
        result = ScrapeResult(
            scrape_job_id=job.id,
            url=u.url,
            product_name=u.product_name,
            barcode=u.barcode,
            status="pending"
        )
        db.add(result)
    db.commit()

    background_tasks.add_task(run_scrape_job, str(job.id))

    return {"job_id": str(job.id), "status": "running", "total_urls": len(req.urls)}


@router.post("/scrape-csv")
async def scrape_csv_upload(file: UploadFile = File(...), background_tasks: BackgroundTasks = None, db: Session = Depends(get_db)):
    content = await file.read()
    text = content.decode('utf-8-sig')

    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        raise HTTPException(status_code=400, detail="Empty CSV file")

    url_columns = []
    name_col = None
    barcode_col = None
    for i, h in enumerate(header):
        h_lower = h.strip().lower()
        if 'url' in h_lower:
            url_columns.append(i)
        if h_lower in ['product name', 'name', 'ürün adı', 'product_name']:
            name_col = i
        if h_lower in ['barcode', 'barkod']:
            barcode_col = i

    if not url_columns:
        raise HTTPException(status_code=400, detail="No URL columns found in CSV")

    urls_to_scrape = []
    for row in reader:
        product_name = row[name_col].strip() if name_col is not None and name_col < len(row) else None
        barcode = row[barcode_col].strip() if barcode_col is not None and barcode_col < len(row) else None

        for col_idx in url_columns:
            if col_idx < len(row):
                url = row[col_idx].strip()
                if url and url.startswith('http'):
                    urls_to_scrape.append({
                        'url': url,
                        'product_name': product_name,
                        'barcode': barcode
                    })

    if not urls_to_scrape:
        raise HTTPException(status_code=400, detail="No valid URLs found in CSV")

    job = ScrapeJob(total_urls=len(urls_to_scrape), status="running")
    db.add(job)
    db.commit()
    db.refresh(job)

    for u in urls_to_scrape:
        result = ScrapeResult(
            scrape_job_id=job.id,
            url=u['url'],
            product_name=u.get('product_name'),
            barcode=u.get('barcode'),
            status="pending"
        )
        db.add(result)
    db.commit()

    background_tasks.add_task(run_scrape_job, str(job.id))

    return {"job_id": str(job.id), "status": "running", "total_urls": len(urls_to_scrape)}


@router.get("/jobs")
async def get_scrape_jobs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    jobs = db.query(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(limit).all()
    return [{
        "id": str(j.id),
        "status": j.status,
        "total_urls": j.total_urls,
        "completed_urls": j.completed_urls,
        "failed_urls": j.failed_urls,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        "error_message": j.error_message
    } for j in jobs]


@router.get("/jobs/{job_id}")
async def get_scrape_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeJob).filter(ScrapeJob.id == uuid_mod.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = db.query(ScrapeResult).filter(ScrapeResult.scrape_job_id == job.id).all()

    return {
        "id": str(job.id),
        "status": job.status,
        "total_urls": job.total_urls,
        "completed_urls": job.completed_urls,
        "failed_urls": job.failed_urls,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "results": [{
            "id": r.id,
            "url": r.url,
            "product_name": r.product_name,
            "barcode": r.barcode,
            "status": r.status,
            "scraped_data": r.scraped_data,
            "error_message": r.error_message
        } for r in results]
    }


@router.get("/jobs/{job_id}/download")
async def download_scrape_results(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeJob).filter(ScrapeJob.id == uuid_mod.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = db.query(ScrapeResult).filter(
        ScrapeResult.scrape_job_id == job.id,
        ScrapeResult.status == "completed"
    ).all()

    export_data = []
    for r in results:
        item = {
            "url": r.url,
            "product_name": r.product_name,
            "barcode": r.barcode,
        }
        if r.scraped_data:
            item.update(r.scraped_data)
        export_data.append(item)

    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=scrape_results_{job_id[:8]}.json"
        }
    )


@router.delete("/jobs/{job_id}")
async def delete_scrape_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeJob).filter(ScrapeJob.id == uuid_mod.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    return {"success": True, "message": "Job deleted"}


async def run_scrape_job(job_id: str):
    from app.services.url_scraper_service import UrlScraperService

    db = SessionLocal()
    try:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == uuid_mod.UUID(job_id)).first()
        if not job:
            return

        job.status = "running"
        db.commit()

        results = db.query(ScrapeResult).filter(
            ScrapeResult.scrape_job_id == job.id,
            ScrapeResult.status == "pending"
        ).all()

        scraper = UrlScraperService()
        await scraper.scrape_urls_batch(results, db)

        completed = db.query(ScrapeResult).filter(
            ScrapeResult.scrape_job_id == job.id,
            ScrapeResult.status == "completed"
        ).count()
        failed = db.query(ScrapeResult).filter(
            ScrapeResult.scrape_job_id == job.id,
            ScrapeResult.status == "failed"
        ).count()

        job.completed_urls = completed
        job.failed_urls = failed
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()
