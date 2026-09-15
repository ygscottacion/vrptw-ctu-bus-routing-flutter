from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.route_matrix_cache import DEFAULT_PROVIDER, DEFAULT_TRAVEL_MODE


class MatrixPointItem(BaseModel):
    lat: float = Field(..., description="Vĩ độ")
    lng: float = Field(..., description="Kinh độ")


class RouteMatrixCacheCreate(BaseModel):
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    distance_km: float
    duration_mins: float
    travel_mode: str = DEFAULT_TRAVEL_MODE
    provider: str = DEFAULT_PROVIDER
    raw_response: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class RouteMatrixCacheResponse(BaseModel):
    id: UUID
    cache_key: str
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    travel_mode: str
    distance_km: float
    duration_mins: float
    provider: str
    raw_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)
