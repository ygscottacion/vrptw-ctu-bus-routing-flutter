import uuid
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.route_matrix_cache import (
    DEFAULT_PROVIDER,
    DEFAULT_TRAVEL_MODE,
    RouteMatrixCache,
    _default_expires_at,
    _utc_now,
)
from app.schemas.route_matrix_cache import RouteMatrixCacheCreate

Coord = Tuple[float, float]
CoordPair = Tuple[Coord, Coord]

_UPSERT_CHUNK_SIZE = 500


def _is_expired(row: RouteMatrixCache, now: datetime) -> bool:
    if row.expires_at is None:
        return False
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= now


def get_by_key(db: Session, cache_key: str) -> Optional[RouteMatrixCache]:
    row = (
        db.query(RouteMatrixCache)
        .filter(RouteMatrixCache.cache_key == cache_key)
        .first()
    )
    if row is None or _is_expired(row, _utc_now()):
        return None
    return row


def get_bulk_matrix(
    db: Session,
    pairs: Sequence[CoordPair],
    travel_mode: str = DEFAULT_TRAVEL_MODE,
) -> List[RouteMatrixCache]:
    """Lấy tất cả bản ghi cache cho danh sách cặp (origin, dest) trong 1 query IN (...)."""
    if not pairs:
        return []

    keys = [
        RouteMatrixCache.generate_cache_key(
            origin[0], origin[1], dest[0], dest[1], travel_mode
        )
        for origin, dest in pairs
    ]
    rows = (
        db.query(RouteMatrixCache)
        .filter(RouteMatrixCache.cache_key.in_(keys))
        .all()
    )
    now = _utc_now()
    return [row for row in rows if not _is_expired(row, now)]


def _record_to_row(record: RouteMatrixCacheCreate) -> dict:
    origin_lat = RouteMatrixCache.round_coord(record.origin_lat)
    origin_lng = RouteMatrixCache.round_coord(record.origin_lng)
    dest_lat = RouteMatrixCache.round_coord(record.dest_lat)
    dest_lng = RouteMatrixCache.round_coord(record.dest_lng)
    travel_mode = (record.travel_mode or DEFAULT_TRAVEL_MODE).upper()
    return {
        "id": uuid.uuid4(),
        "cache_key": RouteMatrixCache.generate_cache_key(
            origin_lat, origin_lng, dest_lat, dest_lng, travel_mode
        ),
        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
        "dest_lat": dest_lat,
        "dest_lng": dest_lng,
        "travel_mode": travel_mode,
        "distance_km": record.distance_km,
        "duration_mins": record.duration_mins,
        "provider": record.provider or DEFAULT_PROVIDER,
        "raw_response": record.raw_response,
        "created_at": _utc_now(),
        "expires_at": record.expires_at or _default_expires_at(),
    }


def upsert_bulk_matrix(
    db: Session,
    records: List[RouteMatrixCacheCreate],
) -> int:
    """
    Bulk upsert theo cache_key (ON CONFLICT DO UPDATE).
    Trả về số dòng đã đưa vào statement (sau khi gộp key trùng trong batch).
    """
    if not records:
        return 0

    dialect = db.get_bind().dialect.name
    insert_fn = pg_insert if dialect == "postgresql" else sqlite_insert
    total = 0

    for offset in range(0, len(records), _UPSERT_CHUNK_SIZE):
        chunk = records[offset : offset + _UPSERT_CHUNK_SIZE]
        rows = [_record_to_row(item) for item in chunk]
        # Giữ bản ghi cuối nếu cùng cache_key trong một chunk (tránh CardinalityViolation).
        deduped = {row["cache_key"]: row for row in rows}
        payload = list(deduped.values())

        stmt = insert_fn(RouteMatrixCache).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["cache_key"],
            set_={
                "origin_lat": stmt.excluded.origin_lat,
                "origin_lng": stmt.excluded.origin_lng,
                "dest_lat": stmt.excluded.dest_lat,
                "dest_lng": stmt.excluded.dest_lng,
                "travel_mode": stmt.excluded.travel_mode,
                "distance_km": stmt.excluded.distance_km,
                "duration_mins": stmt.excluded.duration_mins,
                "provider": stmt.excluded.provider,
                "raw_response": stmt.excluded.raw_response,
                "expires_at": stmt.excluded.expires_at,
            },
        )
        db.execute(stmt)
        total += len(payload)

    db.commit()
    return total
