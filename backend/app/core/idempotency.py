import hashlib
import json
import datetime
from typing import Optional, Tuple, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.idempotency_key import IdempotencyKey


def process_idempotency_key(
    db: Session,
    user_id: UUID,
    endpoint: str,
    key: Optional[str],
    request_data: Any,
) -> Tuple[Optional[IdempotencyKey], Optional[str]]:
    """
    Checks persistent IdempotencyKey in PostgreSQL.
    Returns (existing_record, request_hash).
    Raises HTTP 409 Conflict if key was used with different payload.
    """
    if not key:
        return None, None

    request_str = json.dumps(request_data, default=str, sort_keys=True)
    request_hash = hashlib.sha256(request_str.encode("utf-8")).hexdigest()

    existing = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.key == key,
        )
        .first()
    )

    if existing:
        expires_at = existing.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)

        if expires_at and expires_at <= datetime.datetime.now(datetime.timezone.utc):
            db.delete(existing)
            db.flush()
            return None, request_hash

        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mã X-Idempotency-Key đã được sử dụng với nội dung request khác.",
            )
        return existing, request_hash

    return None, request_hash


def save_idempotency_key(
    db: Session,
    user_id: UUID,
    endpoint: str,
    key: str,
    request_hash: str,
    response_code: int,
    response_body: dict,
    ttl_hours: int = 24,
) -> None:
    """Saves persistent idempotency record in DB."""
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=ttl_hours)
    idempotency_rec = IdempotencyKey(
        user_id=user_id,
        endpoint=endpoint,
        key=key,
        request_hash=request_hash,
        response_code=response_code,
        response_body=response_body,
        expires_at=expires_at,
    )
    db.add(idempotency_rec)
