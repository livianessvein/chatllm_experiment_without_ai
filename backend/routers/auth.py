from __future__ import annotations
from xml.dom.minidom import Text

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import Column
from sqlalchemy.orm import Session

from backend.auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    security,
    verify_password,
)
from backend.database import get_db
from backend.models import TokenBlacklist, User
from backend.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    SignupRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ja cadastrado",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        custom_instructions = Column(Text, nullable=True, default=None)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token, _ = create_access_token(user.email, user.id)
    return AuthResponse(access_token=access_token, email=user.email)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    access_token, _ = create_access_token(user.email, user.id)
    return AuthResponse(access_token=access_token, email=user.email)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao necessaria",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload_decoded = decode_access_token(credentials.credentials)

    blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.jti == payload_decoded["jti"]).first()
    if not blacklisted:
        db.add(TokenBlacklist(jti=payload_decoded["jti"]))
        db.commit()

    return MessageResponse(detail="Logout realizado com sucesso")


@router.get("/me", response_model=AuthResponse)
def me(current_user: User = Depends(get_current_user)):
    return AuthResponse(access_token="", email=current_user.email)