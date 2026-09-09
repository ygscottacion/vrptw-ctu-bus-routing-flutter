"""
test_day8_benchmark_limits_fallback.py — Thành viên 3 (Duy - Routing/Scheduler) — Ngày T8

Nhiệm vụ T8 (đúng theo Implementation Plan 1-2 weeks & team task assignments):
  1. Giới hạn dữ liệu MVP (MVP Data Bounds):
     - test_mvp_data_limits_exceeded: Kiểm thử job với > 100 vé RESERVED bị từ chối với lỗi MVP_DATA_LIMIT_EXCEEDED.
     - test_capacity_exceeded_fallback_error: Kiểm thử khi tổng demand vượt quá tổng capacity xe khả dụng, job báo FAILED với mã CAPACITY_EXCEEDED.

  2. Fallback lỗi (Triple Fallback Strategies):
     - test_osrm_failure_fallback_to_static_matrix: OSRM bị lỗi/timeout (3s) -> Tự động fallback sang Static Matrix (Haversine) -> Job hoàn thành SUCCEEDED.
     - test_tabu_search_failure_fallback_to_sweep: Tabu Search gặp ngoại lệ/lỗi -> Tự động fallback sang Sweep initial solution -> Job hoàn thành SUCCEEDED.

  3. Benchmark hiệu năng & mở rộng quy mô (Benchmark & Data Scaling):
     - test_benchmark_timing_and_data_scaling: Đo thời gian chạy end-to-end (đọc DB -> solve -> ghi DB) với 5, 20, 50, 80 vé, xác nhận đáp ứng ngưỡng MVP (< 15s cho 80 vé).
"""
import math
import time
import uuid
import datetime
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.core.timezone import VN_TZ
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.services.route_worker import run_route_job_worker, RouteStopValidationError
from app.services.vrptw_solver import VRPTWSolverService, RouteSolverError
from app.services.student_routing import config as routing_config
from app.services.student_routing.student_routing_service import StudentRoutingService
from app.services.student_routing.helpers.distance_matrix import OSRMWithFallbackProvider, StaticDistanceMatrixProvider


# ── Patch solver sang static matrix mặc định cho các test không cần network ──────
class _StaticSolverService(VRPTWSolverService):
    def __init__(self):
        super().__init__(use_static_matrix=True)


@pytest.fixture(autouse=True)
def patch_solver(monkeypatch):
    import app.services.route_worker as rw
    monkeypatch.setattr(rw, "VRPTWSolverService", _StaticSolverService)


# ── Helper seed scenario ──────────────────────────────────────────────────────
def _seed_day8_scenario(db: Session, n_bookings: int, service_date: datetime.date, vehicle_capacity: int = 45) -> dict:
    """
    Seed N vé RESERVED, 1 Depot, N trạm đón riêng biệt, và đủ số xe chứa hết N vé.
    """
    depot = Location(
        id=uuid.uuid4(),
        name="ĐH Cần Thơ (Depot)",
        latitude=10.0302,
        longitude=105.7721,
    )
    db.add(depot)

    pickup_locs = []
    tickets = []

    for i in range(n_bookings):
        student = Profile(id=uuid.uuid4(), role=ProfileRole.PASSENGER, full_name=f"Sinh viên Test T8 #{i+1}")
        db.add(student)
        db.flush()

        loc = Location(
            id=uuid.uuid4(),
            name=f"Trạm đón T8 #{i+1}",
            latitude=10.0302 + (i + 1) * 0.0010,
            longitude=105.7721 + (i + 1) * 0.0010,
            demand=1,
            time_window_start=datetime.datetime.combine(service_date, datetime.time(6, 0)),
            time_window_end=datetime.datetime.combine(service_date, datetime.time(7, 30)),
        )
        pickup_locs.append(loc)
        db.add(loc)
        db.flush()

        ticket = Ticket(
            id=uuid.uuid4(),
            user_id=student.id,
            service_date=service_date,
            session_id="MORNING_1",
            trip_type="PICKUP",
            pickup_location_id=loc.id,
            qr_code=f"QR-{uuid.uuid4().hex[:12]}",
            status=TicketStatus.RESERVED,
        )
        tickets.append(ticket)
        db.add(ticket)

    n_vehicles = max(1, math.ceil(n_bookings / vehicle_capacity))
    vehicles = []
    for v in range(n_vehicles):
        driver = Profile(id=uuid.uuid4(), role=ProfileRole.DRIVER, full_name=f"Tài xế T8 #{v+1}")
        db.add(driver)
        db.flush()

        vehicle = Vehicle(
            id=uuid.uuid4(),
            license_plate=f"65B-T8.{uuid.uuid4().hex[:6]}",
            capacity=vehicle_capacity,
            driver_id=driver.id,
        )
        vehicles.append(vehicle)
        db.add(vehicle)

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="PICKUP",
        depot_location_id=depot.id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    return {
        "depot": depot,
        "pickup_locs": pickup_locs,
        "tickets": tickets,
        "vehicles": vehicles,
        "job": job,
    }


# ── Test 1: MVP Data Limits Exceeded (> 100 bookings) ──────────────────────────
def test_mvp_data_limits_exceeded(db_session: Session):
    """
    Tạo 101 vé (> MAX_BOOKINGS_PER_JOB = 100).
    Worker phải báo lỗi MVP_DATA_LIMIT_EXCEEDED và cập nhật job.status = FAILED.
    """
    service_date = datetime.date(2026, 9, 15)
    data = _seed_day8_scenario(db_session, n_bookings=101, service_date=service_date, vehicle_capacity=45)
    job = data["job"]

    with pytest.raises(RouteStopValidationError) as exc_info:
        run_route_job_worker(db_session, job.id)

    assert getattr(exc_info.value, "error_code", "") == "MVP_DATA_LIMIT_EXCEEDED" or "MVP_DATA_LIMIT_EXCEEDED" in str(exc_info.value)

    # Re-query job từ DB để xác nhận trạng thái FAILED và error_message
    updated_job = db_session.query(RouteJob).filter(RouteJob.id == job.id).one()
    assert updated_job.status == RouteJobStatus.FAILED
    assert "[MVP_DATA_LIMIT_EXCEEDED]" in updated_job.error_message


# ── Test 2: Vehicle Capacity Exceeded Fallback Error ───────────────────────────
def test_capacity_exceeded_fallback_error(db_session: Session):
    """
    Tạo 35 vé nhưng chỉ cho 1 xe với capacity = 30 (Demand 35 > Capacity 30).
    Solver phải trả về CAPACITY_EXCEEDED và worker cập nhật job.status = FAILED với thông điệp rõ ràng.
    """
    service_date = datetime.date(2026, 9, 16)
    # Seed 35 vé với 1 xe capacity=30
    depot = Location(id=uuid.uuid4(), name="Depot CTU", latitude=10.0302, longitude=105.7721)
    db_session.add(depot)
    driver = Profile(id=uuid.uuid4(), role=ProfileRole.DRIVER, full_name="Driver Test")
    db_session.add(driver)
    db_session.flush()

    vehicle = Vehicle(id=uuid.uuid4(), license_plate="65B-CAP30", capacity=30, driver_id=driver.id)
    db_session.add(vehicle)

    for i in range(35):
        student = Profile(id=uuid.uuid4(), role=ProfileRole.PASSENGER, full_name=f"Student Cap #{i+1}")
        db_session.add(student)
        db_session.flush()

        loc = Location(
            id=uuid.uuid4(),
            name=f"Trạm Cap #{i+1}",
            latitude=10.0302 + (i + 1) * 0.001,
            longitude=105.7721 + (i + 1) * 0.001,
        )
        db_session.add(loc)
        db_session.flush()

        ticket = Ticket(
            id=uuid.uuid4(),
            user_id=student.id,
            service_date=service_date,
            session_id="MORNING_1",
            trip_type="PICKUP",
            pickup_location_id=loc.id,
            qr_code=f"QR-{uuid.uuid4().hex[:12]}",
            status=TicketStatus.RESERVED,
        )
        db_session.add(ticket)

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="PICKUP",
        depot_location_id=depot.id,
        status=RouteJobStatus.QUEUED,
    )
    db_session.add(job)
    db_session.commit()

    with pytest.raises(RouteStopValidationError) as exc_info:
        run_route_job_worker(db_session, job.id)

    assert getattr(exc_info.value, "error_code", "") == "CAPACITY_EXCEEDED" or "CAPACITY_EXCEEDED" in str(exc_info.value)

    updated_job = db_session.query(RouteJob).filter(RouteJob.id == job.id).one()
    assert updated_job.status == RouteJobStatus.FAILED
    assert "[CAPACITY_EXCEEDED]" in updated_job.error_message


# ── Test 3: OSRM Failure Fallback to Static Distance Matrix ───────────────────
def test_osrm_failure_fallback_to_static_matrix(db_session: Session):
    """
    Giả lập OSRM API bị timeout/lỗi kết nối.
    OSRMWithFallbackProvider tự động fallback sang Static Distance Matrix (Haversine).
    Worker chạy thành công (SUCCEEDED) mà không bị crash.
    """
    provider = OSRMWithFallbackProvider(osrm_url="http://invalid.osrm.server.url/table/v1/", timeout=0.1)
    points = [
        {"lat": 10.0302, "lng": 105.7721},
        {"lat": 10.0315, "lng": 105.7690},
        {"lat": 10.0330, "lng": 105.7680},
    ]
    dist_mat, time_mat, source_used = provider.get_matrix(points, "MORNING_1")

    assert source_used == "STATIC_FALLBACK"
    assert len(dist_mat) == 3
    assert len(time_mat) == 3
    assert dist_mat[0][1] > 0

    # Chạy worker thực tế với OSRM fallback
    service_date = datetime.date(2026, 9, 17)
    data = _seed_day8_scenario(db_session, n_bookings=5, service_date=service_date)
    job = data["job"]

    def mock_get_matrix_fallback(points, time_str_or_session="MORNING_1"):
        return StaticDistanceMatrixProvider().get_matrix(points, time_str_or_session)

    with patch.object(OSRMWithFallbackProvider, "get_matrix", side_effect=mock_get_matrix_fallback):
        completed_job = run_route_job_worker(db_session, job.id)
        assert completed_job.status == RouteJobStatus.SUCCEEDED


# ── Test 4: Tabu Search Failure Fallback to Sweep Initial Solution ────────────
def test_tabu_search_failure_fallback_to_sweep(db_session: Session):
    """
    Giả lập TabuSearchOptimizer.optimize ném ngoại lệ (Exception).
    StudentRoutingService tự động fallback sang kết quả Sweep Clusterer (initial_routes).
    Worker ghi nhận routes từ Sweep và hoàn thành SUCCEEDED.
    """
    service_date = datetime.date(2026, 9, 18)
    data = _seed_day8_scenario(db_session, n_bookings=8, service_date=service_date)
    job = data["job"]

    # Mock TabuSearchOptimizer ném Exception
    def mock_optimize_failing(*args, **kwargs):
        raise RuntimeError("Simulated Tabu Search Memory Out / Converge Exception")

    with patch("app.services.student_routing.core.tabu_optimizer.TabuSearchOptimizer.optimize", side_effect=mock_optimize_failing):
        completed_job = run_route_job_worker(db_session, job.id)
        assert completed_job.status == RouteJobStatus.SUCCEEDED

        routes = db_session.query(Route).filter(Route.route_job_id == job.id).all()
        assert len(routes) > 0
        total_assigned_tickets = sum(r.passenger_count for r in routes)
        assert total_assigned_tickets == 8


# ── Test 5: Benchmark & Data Scaling (5, 20, 50, 80 bookings) ────────────────
def test_benchmark_timing_and_data_scaling(db_session: Session):
    """
    Đo đạc thời gian chạy end-to-end cho 5, 20, 50, 80 vé.
    Kiểm tra tổng thời gian (Read DB + Solve + Write DB) đáp ứng ngưỡng MVP (< 15s cho 80 vé).
    """
    scaling_cases = [5, 20, 50, 80]
    timing_results = {}

    for idx, n in enumerate(scaling_cases):
        service_date = datetime.date(2026, 9, 1) + datetime.timedelta(days=idx * 2)
        data = _seed_day8_scenario(db_session, n_bookings=n, service_date=service_date, vehicle_capacity=45)
        job = data["job"]

        start_time = time.time()
        completed_job = run_route_job_worker(db_session, job.id)
        elapsed = time.time() - start_time

        timing_results[n] = elapsed

        assert completed_job.status == RouteJobStatus.SUCCEEDED

        routes = db_session.query(Route).filter(Route.route_job_id == job.id).all()
        total_tickets = sum(r.passenger_count for r in routes)
        assert total_tickets == n

    # Log kết quả benchmark để theo dõi
    print("\n=================== DAY 8 BENCHMARK RESULTS ===================")
    for n, t in timing_results.items():
        print(f"Bookings: {n:2d} | End-to-End Worker Time: {t:6.3f}s")
    print("===============================================================")

    # Ngưỡng thời gian tối đa chấp nhận cho MVP (80 vé < 15 giây)
    assert timing_results[80] < 15.0, f"Worker time for 80 bookings ({timing_results[80]:.2f}s) exceeded 15s limit."
