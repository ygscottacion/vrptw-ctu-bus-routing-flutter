import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Float, Index, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base

JSONType = JSON().with_variant(JSONB, "postgresql")

COORD_DECIMALS = 5
DEFAULT_TRAVEL_MODE = "DRIVE"
DEFAULT_PROVIDER = "GOOGLE_ROUTES"
DEFAULT_TTL_DAYS = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_expires_at() -> datetime:
    return _utc_now() + timedelta(days=DEFAULT_TTL_DAYS)


class RouteMatrixCache(Base):
    """Cache khoảng cách/thời gian di chuyển giữa hai tọa độ (Google Routes / OSRM)."""

    __tablename__ = "route_matrix_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(String(255), nullable=False)
    origin_lat = Column(Numeric(10, 7), nullable=False)
    origin_lng = Column(Numeric(10, 7), nullable=False)
    dest_lat = Column(Numeric(10, 7), nullable=False)
    dest_lng = Column(Numeric(10, 7), nullable=False)
    travel_mode = Column(String(50), nullable=False, default=DEFAULT_TRAVEL_MODE)
    distance_km = Column(Float, nullable=False)
    duration_mins = Column(Float, nullable=False)
    provider = Column(String(50), nullable=False, default=DEFAULT_PROVIDER)
    raw_response = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False, default=_default_expires_at)

    __table_args__ = (
        Index("idx_cache_key", "cache_key", unique=True),
        Index("idx_origin_dest", "origin_lat", "origin_lng", "dest_lat", "dest_lng"),
    )

    @staticmethod
    def round_coord(value: float) -> float:
        """Làm tròn tọa độ 5 chữ số thập phân (~1.1m) trước khi tạo cache key."""
        return round(float(value), COORD_DECIMALS)

    @staticmethod
    def generate_cache_key(
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        travel_mode: str = DEFAULT_TRAVEL_MODE,
    ) -> str:
        """
        Hash SHA256 của chuỗi tổ hợp tọa độ đã làm tròn + travel_mode.

        Cùng một cặp điểm lệch GPS < ~1m (sau round 5 decimals) cho ra cùng key.
        """
        mode = (travel_mode or DEFAULT_TRAVEL_MODE).upper()
        canonical = (
            f"{RouteMatrixCache.round_coord(origin_lat):.5f},"
            f"{RouteMatrixCache.round_coord(origin_lng):.5f}->"
            f"{RouteMatrixCache.round_coord(dest_lat):.5f},"
            f"{RouteMatrixCache.round_coord(dest_lng):.5f}:"
            f"{mode}"
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
