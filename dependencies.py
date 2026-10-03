import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from database import get_db
from auth import decode_token
from models import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except JWTError as e:
        print(f"DEBUG: JWT decode error: {e}")
        raise credentials_exception

    if payload.get("type") != "access":
        print(f"DEBUG: Token type is not access: {payload.get('type')}")
        raise credentials_exception

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        print("DEBUG: sub is None")
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id_raw)
    except ValueError:
        print(f"DEBUG: Invalid UUID string: {user_id_raw}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        print(f"DEBUG: No user found with UUID: {user_uuid}")
        raise credentials_exception

    return user