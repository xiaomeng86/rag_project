from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import JWT_SECRET_KEY
from exceptions.auth import AuthError
from models.user import User
from utils.password import hash_password, verify_password


JWT_ALGORITHM = "HS256"
access_security = HTTPBearer(auto_error=True)


def create_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(days=2)
    return jwt.encode(
        {
            "sub": str(user.id),
            "user_id": user.id,
            "username": user.username,
            "exp": expires_at,
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def authenticate(db: Session, username: str, password: str) -> str:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("用户名或密码错误")
    return create_token(user)


def register_user(db: Session, username: str, password: str) -> User:
    if not username:
        raise AuthError("用户名不能为空")
    if db.query(User).filter(User.username == username).first():
        raise AuthError("用户名已存在")
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("用户名已存在") from exc
    db.refresh(user)
    return user


def credential_user_id(credentials: HTTPAuthorizationCredentials) -> int:
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        return int(payload["user_id"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的身份凭证",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
