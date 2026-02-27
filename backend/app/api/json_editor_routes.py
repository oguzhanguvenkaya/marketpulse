import uuid as uuid_mod
from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import JsonFile, User
from app.core.auth import get_current_user

router = APIRouter(
    prefix="/api/json-editor",
    tags=["JSON Editor"],
    dependencies=[Depends(get_current_user)],
)


def parse_uuid(file_id: str):
    try:
        return uuid_mod.UUID(file_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid file ID")


class JsonFileCreateRequest(BaseModel):
    filename: str
    content: dict


class JsonFileUpdateRequest(BaseModel):
    content: dict


@router.get("/files")
async def list_files(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    files = db.query(JsonFile).filter(JsonFile.user_id == user.id).order_by(JsonFile.updated_at.desc()).all()
    result = []
    for f in files:
        product_count = 0
        group_name = None
        if f.json_content:
            products = f.json_content.get("products")
            if isinstance(products, list):
                product_count = len(products)
            metadata = f.json_content.get("metadata")
            if isinstance(metadata, dict):
                group_name = metadata.get("group_name")
        result.append({
            "id": str(f.id),
            "filename": f.filename,
            "product_count": product_count,
            "group_name": group_name,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        })
    return result


@router.post("/files")
async def create_file(req: JsonFileCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    json_file = JsonFile(
        filename=req.filename,
        json_content=req.content,
        user_id=user.id,
    )
    db.add(json_file)
    db.commit()
    db.refresh(json_file)

    return {
        "id": str(json_file.id),
        "filename": json_file.filename,
        "json_content": json_file.json_content,
        "created_at": json_file.created_at.isoformat() if json_file.created_at else None,
        "updated_at": json_file.updated_at.isoformat() if json_file.updated_at else None,
    }


@router.get("/files/{file_id}")
async def get_file(file_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    uid = parse_uuid(file_id)
    json_file = db.query(JsonFile).filter(JsonFile.id == uid, JsonFile.user_id == user.id).first()
    if not json_file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "id": str(json_file.id),
        "filename": json_file.filename,
        "json_content": json_file.json_content,
        "created_at": json_file.created_at.isoformat() if json_file.created_at else None,
        "updated_at": json_file.updated_at.isoformat() if json_file.updated_at else None,
    }


@router.put("/files/{file_id}")
async def update_file(file_id: str, req: JsonFileUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    uid = parse_uuid(file_id)
    json_file = db.query(JsonFile).filter(JsonFile.id == uid, JsonFile.user_id == user.id).first()
    if not json_file:
        raise HTTPException(status_code=404, detail="File not found")

    json_file.json_content = req.content
    json_file.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(json_file)

    return {
        "id": str(json_file.id),
        "filename": json_file.filename,
        "json_content": json_file.json_content,
        "created_at": json_file.created_at.isoformat() if json_file.created_at else None,
        "updated_at": json_file.updated_at.isoformat() if json_file.updated_at else None,
    }


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    uid = parse_uuid(file_id)
    json_file = db.query(JsonFile).filter(JsonFile.id == uid, JsonFile.user_id == user.id).first()
    if not json_file:
        raise HTTPException(status_code=404, detail="File not found")

    db.delete(json_file)
    db.commit()
    return {"success": True, "message": "File deleted"}


@router.delete("/files")
async def delete_all_files(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(JsonFile).filter(JsonFile.user_id == user.id).delete()
    db.commit()
    return {"success": True, "message": f"{count} file(s) deleted"}
