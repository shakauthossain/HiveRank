import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBasic, HTTPBasicCredentials
import secrets
from app.database import SessionLocal, close_db
from app.models import User
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here_change_it_now!")
ALGORITHM = "HS256"
def _access_token_expire_minutes() -> int:
    raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    try:
        minutes = int(raw)
    except ValueError:
        minutes = 120
    return max(minutes, 60)


ACCESS_TOKEN_EXPIRE_MINUTES = _access_token_expire_minutes()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
oauth2_scheme_mandatory = OAuth2PasswordBearer(tokenUrl="token", auto_error=True)

import bcrypt

def get_password_hash(password: str):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str):
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def _user_from_email(email: str) -> Optional[User]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            db.expunge(user)
        return user
    finally:
        close_db(db)


async def get_current_user(token: str = Depends(oauth2_scheme_mandatory)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = _user_from_email(email)
    if user is None:
        raise credentials_exception
    return user

async def get_optional_user(token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    return _user_from_email(email)

security_basic = HTTPBasic()
security_basic_optional = HTTPBasic(auto_error=False)


def _is_env_super_admin(credentials: HTTPBasicCredentials) -> bool:
    correct_username = os.getenv("ADMIN_EMAIL", "admin@seo.com")
    correct_password = os.getenv("ADMIN_PASSWORD", "supersecureadmin123")
    return secrets.compare_digest(
        credentials.username, correct_username
    ) and secrets.compare_digest(credentials.password, correct_password)


def get_super_admin(credentials: HTTPBasicCredentials = Depends(security_basic)):
    if not _is_env_super_admin(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def user_permissions(user: User) -> dict:
    """Module flags for dashboard nav / Access UI."""
    return {
        "analyze": bool(getattr(user, "can_analyze", True)),
        "snapshot": bool(getattr(user, "can_snapshot", True)),
        "bulk": bool(getattr(user, "can_bulk", True)),
        "quick_audit": bool(getattr(user, "can_quick_audit", True)),
        "access": bool(getattr(user, "can_access", False)),
    }


def role_label_from_permissions(perms: dict) -> str:
    a, s, b, q, x = (
        perms.get("analyze"),
        perms.get("snapshot"),
        perms.get("bulk"),
        perms.get("quick_audit"),
        perms.get("access"),
    )
    if x and a and s and b and q:
        return "Access admin"
    if a and s and b and q and not x:
        return "Operator"
    if a and q and not s and not b and not x:
        return "Analyze + Quick"
    if a and not s and not b and not q and not x:
        return "Analyze only"
    if q and not a and not s and not b and not x:
        return "Quick Audit only"
    if not a and not s and not b and not q and not x:
        return "No access"
    return "Custom"


def preset_permissions(preset: str) -> dict:
    key = (preset or "operator").strip().lower().replace(" ", "_")
    if key in ("analyze_only", "analyze"):
        return {
            "can_analyze": True,
            "can_snapshot": False,
            "can_bulk": False,
            "can_quick_audit": False,
            "can_access": False,
        }
    if key in ("quick_only", "quick_audit"):
        return {
            "can_analyze": False,
            "can_snapshot": False,
            "can_bulk": False,
            "can_quick_audit": True,
            "can_access": False,
        }
    if key in ("access_admin", "superadmin", "admin"):
        return {
            "can_analyze": True,
            "can_snapshot": True,
            "can_bulk": True,
            "can_quick_audit": True,
            "can_access": True,
        }
    # operator default
    return {
        "can_analyze": True,
        "can_snapshot": True,
        "can_bulk": True,
        "can_quick_audit": True,
        "can_access": False,
    }


async def get_admin_actor(
    credentials: Optional[HTTPBasicCredentials] = Depends(security_basic_optional),
    user: Optional[User] = Depends(get_optional_user),
) -> str:
    """Env superadmin (Basic) or JWT user with Access admin permission."""
    if credentials is not None and _is_env_super_admin(credentials):
        return credentials.username
    if user is not None and bool(getattr(user, "can_access", False)):
        return user.email
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin access required",
        headers={"WWW-Authenticate": "Basic"},
    )


def require_permission(flag: str):
    """Dependency factory: JWT user must have a module flag."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        perms = user_permissions(user)
        if not perms.get(flag):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {flag}",
            )
        return user

    return _check
