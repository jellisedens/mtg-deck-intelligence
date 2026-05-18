import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from services.email import send_verification_email
from api.schemas.auth import (
    SignupRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    verification_token = secrets.token_urlsafe(32)

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    send_verification_email(user.email, verification_token)

    return TokenResponse(
        access_token=create_access_token(user_id=str(user.id), email=user.email),
        refresh_token=create_refresh_token(user_id=str(user.id)),
        is_verified=user.is_verified,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenResponse(
        access_token=create_access_token(user_id=str(user.id), email=user.email),
        refresh_token=create_refresh_token(user_id=str(user.id)),
        is_verified=user.is_verified,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_refresh_token(request.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return TokenResponse(
        access_token=create_access_token(user_id=str(user.id), email=user.email),
        refresh_token=create_refresh_token(user_id=str(user.id)),
        is_verified=user.is_verified,
    )


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify email via the link token."""
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user.is_verified = True
    user.verification_token = None
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
def resend_verification(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resend verification email to the authenticated user."""
    if user.is_verified:
        return {"message": "Email already verified"}

    token = secrets.token_urlsafe(32)
    user.verification_token = token
    db.commit()

    send_verification_email(user.email, token)

    return {"message": "Verification email sent"}