
from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


CONVERSATION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_conversation_id(value: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError("Conversation ID cannot be empty")

    if len(value) > 100:
        raise ValueError("Conversation ID cannot exceed 100 characters")

    if not CONVERSATION_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "Conversation ID may contain only letters, numbers, "
            "hyphens, and underscores"
        )

    return value


class TutorRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str = Field(
        default="default",
        min_length=1,
        max_length=100,
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Question cannot be empty")

        return value

    @field_validator("conversation_id")
    @classmethod
    def validate_request_conversation_id(cls, value: str) -> str:
        return validate_conversation_id(value)


class TutorAnswerResponse(BaseModel):
    conversation_id: str
    question: str
    answer: str = Field(max_length=20000)


class TutorHistoryMessage(BaseModel):
    id: int
    role: Literal["human", "ai", "user", "assistant"]
    content: str = Field(max_length=20000)
    created_at: datetime


class TutorHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[TutorHistoryMessage]
