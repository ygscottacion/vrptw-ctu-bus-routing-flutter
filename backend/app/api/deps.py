import json
import urllib.request
import uuid
import warnings
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.crud import crud_user
from app.models.profile import Profile, ProfileRole
from app.models.user import User, UserRole
from app.schemas.user import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Cache for JWKS keys
_jwks_cache: Dict[str, Any] = {}


def get_jwks(jwks_url: str) -> Dict[str, Any]:
    """Fetch and cache JWKS keys from Supabase Auth URL."""
    if not jwks_url:
        return {}
    if jwks_url in _jwks_cache:
        return _jwks_cache[jwks_url]
    try:
        req = urllib.request.Request(jwks_url, headers={"User-Agent": "FastAPI-JWKS"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _jwks_cache[jwks_url] = data
            return data
    except Exception:
        return {}


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Verify Supabase JWT access token using JWKS (asymmetric) or SUPABASE_JWT_SECRET (HS256).
    Performs strict validation of signature, exp, iss, aud, and sub claims.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        raise credentials_exception

    alg = header.get("alg", "HS256")
    kid = header.get("kid")

    payload: Optional[Dict[str, Any]] = None

    if alg == "HS256":
        if not settings.SUPABASE_JWT_SECRET:
            raise credentials_exception
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except JWTError:
            raise credentials_exception
    else:
        # Asymmetric signature (RS256, ES256, etc.) via JWKS
        jwks = get_jwks(settings.SUPABASE_JWKS_URL)
        keys = jwks.get("keys", [])
        matching_key = None
        for k in keys:
            if kid and k.get("kid") == kid:
                matching_key = k
                break
        if not matching_key and keys:
            matching_key = keys[0]

        if not matching_key:
            raise credentials_exception

        try:
            payload = jwt.decode(
                token,
                matching_key,
                algorithms=[alg],
                options={"verify_aud": False},
            )
        except JWTError:
            raise credentials_exception

    if not payload:
        raise credentials_exception

    # Validate Audience claim strictly
    aud = payload.get("aud")
    aud_valid = (aud == "authenticated") if isinstance(aud, str) else (isinstance(aud, list) and "authenticated" in aud)
    if not aud_valid:
        raise credentials_exception

    # Validate Issuer claim (if configured)
    if settings.SUPABASE_ISSUER:
        token_iss = payload.get("iss", "").rstrip("/")
        expected_iss = settings.SUPABASE_ISSUER.rstrip("/")
        if token_iss != expected_iss:
            raise credentials_exception

    # Validate Subject claim (must be valid UUID)
    sub = payload.get("sub")
    if not sub:
        raise credentials_exception

    try:
        uuid.UUID(str(sub))
    except (ValueError, TypeError):
        raise credentials_exception

    return payload


def get_current_profile(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> Profile:
    """
    Authenticate request via Supabase Auth JWT and return Profile model.
    Safely auto-creates default PASSENGER profile if missing.
    """
    payload = verify_supabase_jwt(token)
    user_id = UUID(str(payload["sub"]))

    profile = db.query(Profile).filter(Profile.id == user_id).first()
    if not profile:
        # Safely create default PASSENGER profile in transaction
        try:
            user_meta = payload.get("user_metadata") or {}
            full_name = user_meta.get("full_name") or payload.get("email")
            phone = user_meta.get("phone")

            # Ensure auth.users entry exists for FK constraint in dev/test DB
            try:
                db.execute(
                    text("INSERT INTO auth.users (id, aud, role) VALUES (:id, 'authenticated', 'authenticated') ON CONFLICT (id) DO NOTHING"),
                    {"id": str(user_id)},
                )
                db.commit()
            except Exception:
                db.rollback()

            profile = Profile(
                id=user_id,
                role=ProfileRole.PASSENGER,
                full_name=full_name,
                phone=phone,
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        except Exception:
            db.rollback()
            profile = db.query(Profile).filter(Profile.id == user_id).first()
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not initialize profile for user",
                )

    # Attach email dynamically for response building if present
    setattr(profile, "email", payload.get("email"))
    return profile


def get_current_admin(
    current_profile: Profile = Depends(get_current_profile),
) -> Profile:
    """Ensure authenticated user has ADMIN role."""
    if current_profile.role != ProfileRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges (admin required)",
        )
    return current_profile


def get_current_driver(
    current_profile: Profile = Depends(get_current_profile),
) -> Profile:
    """Ensure authenticated user has DRIVER or ADMIN role."""
    if current_profile.role not in (ProfileRole.DRIVER, ProfileRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges (driver or admin required)",
        )
    return current_profile


def get_current_student(
    current_profile: Profile = Depends(get_current_profile),
) -> Profile:
    """Ensure authenticated user has PASSENGER (student) or ADMIN role."""
    if current_profile.role not in (ProfileRole.PASSENGER, ProfileRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges (student/passenger or admin required)",
        )
    return current_profile


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    DEPRECATED: Legacy JWT authentication for un-migrated endpoints depending on integer users.id.
    Will be removed in Day 3 after business tables migrate to Profile UUID.
    """
    warnings.warn(
        "get_current_user is deprecated. Use get_current_profile instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenPayload(sub=username)
    except (JWTError, ValidationError):
        raise credentials_exception

    user = crud_user.get_user_by_username(db, username=token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user
