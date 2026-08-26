from fastapi import APIRouter, Depends, status
from app.services.student_routing.schemas import (
    SchoolConfig, Vehicle, Station, OptimizationOptions, OptimizationResponse
)
from app.services.student_routing.student_routing_service import StudentRoutingService
from pydantic import BaseModel

router = APIRouter()
routing_service = StudentRoutingService()


class StudentRoutingOptimizeRequest(BaseModel):
    school_config: SchoolConfig
    vehicles: list[Vehicle]
    stations: list[Station]
    options: OptimizationOptions


@router.post("/optimize", response_model=OptimizationResponse, status_code=status.HTTP_200_OK)
def optimize_student_routes(payload: StudentRoutingOptimizeRequest) -> OptimizationResponse:
    """
    Endpoint tối ưu hóa lộ trình xe buýt đưa đón sinh viên (CTU Student Routing Service).
    Sử dụng Sweep Algorithm (Khởi tạo Lời giải Ban đầu) & Tabu Search (Tối ưu Lộ trình & VRPTW).
    """
    return routing_service.optimize_routes(
        school_config=payload.school_config,
        vehicles=payload.vehicles,
        stations=payload.stations,
        options=payload.options
    )
