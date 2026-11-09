
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.db.connection import SessionLocal
from app.db.models import TutorMessage
from app.services.tutor import ask_tutor as generate_tutor_answer
from app.schemas.tutor import (
    TutorRequest,
    TutorAnswerResponse,
    TutorHistoryResponse,
    validate_conversation_id,
)

import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tutor", tags=["Tutor"])


def get_valid_conversation_id(conversation_id: str) -> str:
    try:
        return validate_conversation_id(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Invalid conversation ID",
        )


@router.post("/ask", response_model=TutorAnswerResponse)
def ask_tutor_endpoint(request: TutorRequest):
    try:
        answer = generate_tutor_answer(
            request.question,
            request.conversation_id,
        )

        return {
            "conversation_id": request.conversation_id,
            "question": request.question,
            "answer": answer,
        }

    except Exception:
        logger.exception("Tutor request failed")
        raise HTTPException(
            status_code=502,
            detail="The AI tutor could not generate an answer",
    )


@router.get("/history", response_model=TutorHistoryResponse)
def get_tutor_history(
    conversation_id: str = "default",
    limit: int = Query(default=20, ge=1, le=100),
):
    conversation_id = get_valid_conversation_id(conversation_id)

    try:
        with SessionLocal() as db:
            recent_messages = db.scalars(
                select(TutorMessage)
                .where(
                    TutorMessage.conversation_id == conversation_id
                )
                .order_by(TutorMessage.id.desc())
                .limit(limit)
            ).all()

            # Return oldest-first so the chat displays in conversation order.
            messages = list(reversed(recent_messages))

            return {
                "conversation_id": conversation_id,
                "messages": [
                    {
                        "id": message.id,
                        "role": message.role,
                        "content": message.content,
                        "created_at": message.created_at,
                    }
                    for message in messages
                ],
            }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve tutor history",
        )


@router.delete("/conversations/{conversation_id}")
def delete_tutor_conversation(conversation_id: str):
    conversation_id = get_valid_conversation_id(conversation_id)

    if conversation_id == "default":
        raise HTTPException(
            status_code=400,
            detail="The original conversation cannot be deleted",
        )

    try:
        with SessionLocal() as db:
            with db.begin():
                result = db.execute(
                    delete(TutorMessage).where(
                        TutorMessage.conversation_id == conversation_id
                    )
                )

                deleted_count = result.rowcount or 0

            return {
                "conversation_id": conversation_id,
                "deleted_messages": deleted_count,
                "success": True,
            }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not delete the conversation",
        )
