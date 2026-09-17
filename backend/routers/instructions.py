from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import User
from backend.services.openrouter import _SYSTEM_PROMPT

router = APIRouter(prefix="/instructions", tags=["instructions"])

MAX_INSTRUCTIONS_LENGTH = 4000

class InstructionsResponse(BaseModel):
    custom_instructions: str
    is_default: bool
    default_instructions: str


class InstructionsUpdate(BaseModel):
    custom_instructions: str = Field(default="", max_length=MAX_INSTRUCTIONS_LENGTH)


def _to_response(user: User) -> InstructionsResponse:
    stored = (user.custom_instructions or "").strip()
    return InstructionsResponse(
        custom_instructions=stored,
        is_default=not stored,
        default_instructions=_SYSTEM_PROMPT,
    )


@router.get("", response_model=InstructionsResponse)
def read_instructions(current_user: User = Depends(get_current_user)) -> InstructionsResponse:
    return _to_response(current_user)


@router.put("", response_model=InstructionsResponse)
def update_instructions(
    payload: InstructionsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InstructionsResponse:
    cleaned = payload.custom_instructions.strip()
    current_user.custom_instructions = cleaned or None
    db.commit()
    db.refresh(current_user)
    return _to_response(current_user)