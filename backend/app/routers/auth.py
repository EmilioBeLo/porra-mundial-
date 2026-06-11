import bcrypt
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import AuthRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _hash_password(password: str) -> str:
    # Encode the password string to bytes
    pwd_bytes = password.encode('utf-8')
    # Generate salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    # Decode back to string for database storage
    return hashed.decode('utf-8')


def _verify_password(plain: str, hashed: str) -> bool:
    plain_bytes = plain.encode('utf-8')
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def _create_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user.nombre,
        "user_id": user.id,
        "is_admin": user.is_admin,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: AuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user and return a JWT token."""
    existing = db.query(User).filter(User.nombre == body.nombre).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese nombre",
        )

    user = User(
        nombre=body.nombre,
        password_hash=_hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_token(user)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        nombre=user.nombre,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: AuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate user and return a JWT token."""
    user = db.query(User).filter(User.nombre == body.nombre).first()
    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre o contraseña incorrectos",
        )

    token = _create_token(user)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        nombre=user.nombre,
        is_admin=user.is_admin,
    )
