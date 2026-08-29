import logging
from datetime import datetime, time, timedelta

from typing import Any, List, Optional
# BỔ SUNG: Đã thêm Query vào dòng import này
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.core.database import SessionLocal
from app.crud import crud_route, crud_ticket
from app.models.location import Location
from app.models.route import RouteStatus
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.schemas.route import (
    RouteResponse,
    RouteGenerateRequest,
    RouteGenerationAcceptedResponse,
    RouteGenerationJobStatusResponse,
)
from app.services.job_store import JobStatus, route_job_store
from app.services.vrptw_solver import VRPTWSolverService
from app.services.student_routing.schemas import SessionId, TripType
from app.services.demand_adapter import DemandAdapter, RoutingValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[RouteResponse])
def list_active_routes(
    db: Session = Depends(deps.get_db),
    current_student: User = Depends(deps.get_current_student),
    # BỔ SUNG: Khai báo tham số location_name ở đây
    location_name: Optional[str] = Query(None, description="Lọc tuyến xe theo tên trạm đón (Hỗ trợ tìm kiếm tương đối)")
) -> Any:
    """
    Danh sách các tuyến đang khả dụng HÔM NAY để hành khách chọn khi mua vé
    (status = pending hoặc in_progress). Mỗi tuyến kèm danh sách stops (trạm dừng
    theo thứ tự) để Flutter hiển thị tên tuyến / lộ trình.

    Student hoặc Admin.
    """
    # Biến location_name giờ đã tồn tại hợp lệ
    return crud_route.get_active_routes(db, location_name=location_name)


def _run_route_generation_job(
    job_id: str,
    depot_dict: dict,
    locations_dict: List[dict],
    vehicles_dict: List[dict],
    route_date,
    session_id: str,
    trip_type: str,
) -> None:
    """
    Hàm chạy nền (được fastapi.BackgroundTasks gọi SAU KHI response 202 đã trả về
    cho client), thực hiện phần tốn thời gian: Sweep + Tabu Search rồi ghi kết quả
    vào DB.

    QUAN TRỌNG: hàm này KHÔNG tái sử dụng Session được inject vào endpoint (qua
    Depends(deps.get_db)) vì session đó gắn với vòng đời request và có thể đã bị
    đóng khi background task thực sự chạy. Thay vào đó, mở một Session mới độc lập.
    """
    route_job_store.mark_processing(job_id)
    db: Session = SessionLocal()
    try:
        solver = VRPTWSolverService()
        results = solver.solve(
            depot_dict, locations_dict, vehicles_dict,
            session_id=SessionId(session_id), trip_type=TripType(trip_type.upper()),
        )

        created_route_ids: List[int] = []
        for res in results:
            route_obj = crud_route.create_route(
                db=db,
                vehicle_id=res["vehicle_id"],
                route_date=route_date,
                total_distance=res["total_distance_km"],
                stops_data=res["ordered_stops"],
            )
            created_route_ids.append(route_obj.id)
            stop_ids = {int(stop["id"]) for stop in res["ordered_stops"]}
            for ticket in crud_ticket.get_unassigned_tickets_for_run(
                db, route_date, session_id, trip_type
            ):
                if ticket.pickup_location_id in stop_ids:
                    ticket.route_id = route_obj.id
            db.commit()

        route_job_store.mark_completed(job_id, route_ids=created_route_ids)
    except Exception as exc:  # noqa: BLE001 - ghi lại lỗi để client poll thấy được
        logger.exception("VRPTW route generation job %s failed", job_id)
        db.rollback()
        route_job_store.mark_failed(job_id, error_message=str(exc))
    finally:
        db.close()


@router.post(
    "/generate",
    response_model=RouteGenerationAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_routes(
    request: RouteGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
) -> Any:
    """
    Kích hoạt VRPTW Solver Pipeline (Sweep + Tabu Search) một cách BẤT ĐỒNG BỘ
    thông qua fastapi.BackgroundTasks.

    Endpoint chỉ thực hiện các truy vấn NHANH (kiểm tra depot, load danh sách
    trạm/xe) một cách đồng bộ, rồi trả về NGAY (202 Accepted) kèm job_id. Việc
    giải thuật toán (có thể mất vài giây với dữ liệu thực tế nhiều trạm/nhiều xe)
    được đẩy sang chạy nền, tránh làm client (Flutter) bị treo/timeout khi chờ.

    Flutter client nên poll:
        GET /api/v1/routes/generate/status/{job_id}
    để lấy trạng thái (pending -> processing -> completed/failed) và kết quả.

    Admin only.
    """
    depot_loc = db.query(Location).filter(Location.id == request.depot_location_id).first()
    if not depot_loc:
        raise HTTPException(status_code=404, detail="Depot location not found")

    if request.trip_type not in {"pickup", "dropoff"}:
        raise HTTPException(status_code=422, detail="trip_type phải là pickup hoặc dropoff.")
    if request.session_id not in {item.value for item in SessionId}:
        raise HTTPException(status_code=422, detail="session_id không hợp lệ.")
    cutoff = datetime.combine(request.date - timedelta(days=1), time(hour=22))
    if datetime.now() < cutoff:
        raise HTTPException(
            status_code=400,
            detail="Chỉ được sinh tuyến sau 22:00 của ngày trước ngày chạy.",
        )

    reserved_tickets = crud_ticket.get_unassigned_tickets_for_run(
        db, request.date, request.session_id, request.trip_type
    )
    demand_by_location = DemandAdapter.aggregate_tickets_to_station_demands(reserved_tickets)
    if not demand_by_location:
        raise HTTPException(status_code=400, detail="Không có vé lượt đã chốt cho ca này.")

    locations_db = db.query(Location).filter(Location.id.in_(demand_by_location.keys())).all()
    vehicles_db = db.query(Vehicle).all()

    try:
        depot_dict, locations_dict, vehicles_dict = DemandAdapter.build_solver_inputs(
            depot=depot_loc,
            stations=locations_db,
            vehicles=vehicles_db,
            station_demands=demand_by_location,
        )
    except RoutingValidationError as err:
        raise HTTPException(status_code=400, detail=str(err))

    job_id = route_job_store.create_job(requested_by_user_id=current_admin.id)

    background_tasks.add_task(
        _run_route_generation_job,
        job_id,
        depot_dict,
        locations_dict,
        vehicles_dict,
        request.date,
        request.session_id,
        request.trip_type,
    )

    return RouteGenerationAcceptedResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Route generation started in background. Poll GET /generate/status/{job_id} for the result.",
    )


@router.get("/generate/status/{job_id}", response_model=RouteGenerationJobStatusResponse)
def get_route_generation_status(
    job_id: str,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
) -> Any:
    """
    Poll trạng thái/kết quả của một job sinh lộ trình được tạo bởi POST /generate.
    Admin only.
    """
    job = route_job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Route generation job not found")

    routes: List = []
    if job["status"] == JobStatus.COMPLETED and job["route_ids"]:
        routes = crud_route.get_routes_by_ids(db, route_ids=job["route_ids"])

    return RouteGenerationJobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        error_message=job["error_message"],
        routes=routes,
    )


@router.get("/details/{route_id}", response_model=RouteResponse)
def get_route_details(
    route_id: int,
    db: Session = Depends(deps.get_db),
    current_driver: User = Depends(deps.get_current_driver)
) -> Any:
    """
    Get detailed route stops and coordinates for Flutter Map rendering.
    Driver or Admin only.
    """
    route = crud_route.get_route_by_id(db, route_id=route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


def _ensure_route_driver(route, current_driver: User) -> None:
    """A driver can only change the route assigned to their own vehicle."""
    if current_driver.role == UserRole.ADMIN:
        return
    if not route.vehicle_id or not route.vehicle or route.vehicle.driver_id != current_driver.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Route is not assigned to this driver")


@router.patch("/{route_id}/start", response_model=RouteResponse)
def start_route(
    route_id: int,
    db: Session = Depends(deps.get_db),
    current_driver: User = Depends(deps.get_current_driver),
) -> Any:
    route = crud_route.get_route_by_id(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    _ensure_route_driver(route, current_driver)
    return crud_route.update_route_status(db, route, RouteStatus.IN_PROGRESS)


@router.patch("/{route_id}/end", response_model=RouteResponse)
def end_route(
    route_id: int,
    db: Session = Depends(deps.get_db),
    current_driver: User = Depends(deps.get_current_driver),
) -> Any:
    route = crud_route.get_route_by_id(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    _ensure_route_driver(route, current_driver)
    return crud_route.update_route_status(db, route, RouteStatus.COMPLETED)


@router.get("/driver/{driver_id}", response_model=List[RouteResponse])
def get_driver_routes(
    driver_id: int,
    db: Session = Depends(deps.get_db),
    current_driver: User = Depends(deps.get_current_driver)
) -> Any:
    """
    Get assigned daily bus routes for a specific driver.
    Driver or Admin only. A driver may only view their own schedule.
    """
    if current_driver.role == UserRole.DRIVER and current_driver.id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drivers can only view their own assigned routes"
        )
    return crud_route.get_routes_by_driver(db, driver_id=driver_id)
