"""AI Musteri Hizmetleri API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.customer_questions_service import customer_questions_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customer-questions", tags=["Customer Questions"])


@router.get("/pending")
async def get_pending_questions(
    platform: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bekleyen musteri sorularini listele."""
    return await customer_questions_service.get_pending_questions(user, db, platform)


class GenerateAnswerRequest(BaseModel):
    question_id: str
    custom_context: Optional[str] = None
    store_policies: Optional[dict] = None


@router.post("/generate-answer")
async def generate_answer(
    req: GenerateAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI ile musteri sorusuna yanit olustur."""
    return await customer_questions_service.generate_ai_answer(
        user, db, req.question_id, req.custom_context, req.store_policies
    )


class ApproveAnswerRequest(BaseModel):
    question_id: str
    answer: str
    edited: bool = False


@router.post("/approve-send")
async def approve_and_send(
    req: ApproveAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Onayli yaniti pazaryerine gonder."""
    return await customer_questions_service.approve_and_send(
        user, db, req.question_id, req.answer, req.edited
    )


@router.get("/history")
async def get_answer_history(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Yanit gecmisi ve basari orani."""
    return await customer_questions_service.get_answer_history(user, db, limit)


class StorePoliciesRequest(BaseModel):
    policies: dict


@router.put("/store-policies")
async def update_store_policies(
    req: StorePoliciesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Magaza politikalarini guncelle."""
    return await customer_questions_service.update_store_policies(
        user, db, req.policies
    )
