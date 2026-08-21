from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from exceptions.auth import AuthError
from schemas.auth import CredentialsRequest, RegisterResponse, TokenResponse
from service.auth import authenticate, register_user
from utils.database import get_db


router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(request: CredentialsRequest, db: Session = Depends(get_db)):
    try:
        user = register_user(db, request.username.strip(), request.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RegisterResponse(user_id=user.id, username=user.username)


@router.post("/login", response_model=TokenResponse)
def login(request: CredentialsRequest, db: Session = Depends(get_db)):
    try:
        return TokenResponse(
            access_token=authenticate(db, request.username.strip(), request.password)
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
