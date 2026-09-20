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


@router.get("/benchmark/60-students", status_code=status.HTTP_200_OK)
def run_60_students_benchmark(num_vehicles: int = 2, num_stations: int = 20, num_runs: int = 1):
    """
    Endpoint benchmark phục vụ Khánh (Frontend/API) đối sánh Baseline vs Tabu Search
    trên kịch bản 60 sinh viên quanh CTU (chia vào >= 2 xe, chặn quá tải/quá giờ) cho ngày 14.
    """
    from app.services.student_routing.benchmark import StudentRoutingBenchmark
    benchmark = StudentRoutingBenchmark()
    return benchmark.run_60_students_scenario(
        num_vehicles=num_vehicles,
        num_stations=num_stations,
        num_runs=num_runs
    )

