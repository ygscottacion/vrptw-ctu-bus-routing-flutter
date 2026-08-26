from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TripType(str, Enum):
    PICKUP = "PICKUP"
    DROPOFF = "DROPOFF"


class SessionId(str, Enum):
    MORNING_1 = "MORNING_1"
    MORNING_2 = "MORNING_2"
    NOON_1 = "NOON_1"
    NOON_2 = "NOON_2"


class TimeWindowPolicy(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    ELASTIC = "ELASTIC"


class VehicleStatus(str, Enum):
    IDLE_AT_SCHOOL = "IDLE_AT_SCHOOL"
    ON_PICKUP = "ON_PICKUP"
    ON_DROPOFF = "ON_DROPOFF"
    IDLE_AT_DEPOT = "IDLE_AT_DEPOT"
    UNAVAILABLE = "UNAVAILABLE"


class LocationSchema(BaseModel):
    lat: float
    lng: float


class SchoolConfig(BaseModel):
    school_id: str = "CTU-MAIN"
    school_name: str = "Trường Đại học Cần Thơ"
    location: LocationSchema = Field(default_factory=lambda: LocationSchema(lat=10.0302, lng=105.7721))
    buffer_minutes: int = 15
    boarding_at_school_minutes: int = 10
    max_ride_time_minutes: int = 45
    service_radius_km: float = 10.0


class Vehicle(BaseModel):
    id: str
    capacity: int = 45
    available_from: str = "05:00"
    start_location: Optional[LocationSchema] = None
    status: VehicleStatus = VehicleStatus.IDLE_AT_SCHOOL


class Station(BaseModel):
    id: str
    name: str
    location: LocationSchema
    distance_from_school_km: Optional[float] = None
    time_window_start: str  # HH:MM
    time_window_end: str    # HH:MM
    pickup_student_count: int = 0
    dropoff_student_count: int = 0


class OptimizationOptions(BaseModel):
    session_id: SessionId
    trip_type: TripType = TripType.PICKUP
    generate_return_trip: bool = False
    enable_path_flexibility: bool = True
    tabu_max_iterations: int = 300
    tabu_tenure: int = 10


class Stop(BaseModel):
    sequence: int
    station_id: str
    station_name: str
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    students_picked: int = 0
    students_dropped: int = 0
    current_load: int = 0
    within_time_window: bool = True


class Route(BaseModel):
    route_id: str
    trip_type: TripType
    session_id: SessionId
    vehicle_id: str
    departure_time: str
    arrival_at_school: str
    total_students: int
    total_distance_km: float
    stops: List[Stop]


class InfeasibleStation(BaseModel):
    station_id: str
    reason: str
    detail: str


class PartialResult(BaseModel):
    feasible_stations: List[str] = Field(default_factory=list)
    infeasible_stations: List[InfeasibleStation] = Field(default_factory=list)


class RouteSummary(BaseModel):
    total_routes: int
    total_vehicles_used: int
    total_students_served: int
    total_students_requested: int
    total_distance_km: float
    school_arrival_time: str


class RouteDataPayload(BaseModel):
    summary: RouteSummary
    routes: List[Route]


class OptimizationResponse(BaseModel):
    status: str  # SUCCESS | ERROR | PARTIAL_SUCCESS
    session_id: SessionId
    trip_type: TripType
    optimized_at: str
    data: Optional[RouteDataPayload] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    partial_result: Optional[PartialResult] = None
