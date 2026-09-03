"""
test_day6_rerun_benchmark.py — Thành viên 3 (Duy - Routing/Scheduler) — Ngày T6

Nhiệm vụ T6:
  1. test_rerun_job_does_not_create_duplicate_routes:
       Gọi run_route_job_worker 2 lần với cùng job → xác nhận Route/RouteStop
       KHÔNG tăng thêm ở lần 2 (idempotency khi rerun).

  2. test_worker_e2e_benchmark_timing:
       Đo thời gian chạy toàn bộ worker (đọc DB → Sweep/Tabu → ghi DB) ở
       3 mốc kích thước: 5, 15, 30 booking.
       Không assert threshold cứng — mục đích là GHI NHẬN số liệu để tham khảo.

Ngữ cảnh:
  - test_day5_integration.py đã xác nhận luồng đúng (9/9 pass): booking → SUCCEEDED.
  - test_vrptw.py::test_scaling_10_20_50_stops đo riêng phần solver (Sweep+Tabu),
    KHÔNG tính thời gian đọc/ghi DB — benchmark hôm nay bổ sung phần còn thiếu đó.
  - Solver được monkey-patch sang static matrix để bỏ qua OSRM (không cần network).
"""
import time
import uuid
import datetime
import pytest
from sqlalchemy.orm import Session

from app.core.timezone import VN_TZ
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.services.route_worker import run_route_job_worker
from app.services.vrptw_solver import VRPTWSolverService


# ── Patch solver sang static matrix (bypass OSRM) ────────────────────────────
class _StaticSolverService(VRPTWSolverService):
    def __init__(self):
        super().__init__(use_static_matrix=True)


@pytest.fixture(autouse=True)
def patch_solver(monkeypatch):
    import app.services.route_worker as rw
    monkeypatch.setattr(rw, "VRPTWSolverService", _StaticSolverService)


# ── Helper: seed N booking + 1 depot + N pickup locations + đủ xe ─────────────
def _seed_scenario(db: Session, n_bookings: int, service_date: datetime.date) -> dict:
    """
    Seed dữ liệu để đủ chạy n_bookings vé cho 1 ca.
    Mỗi vé ở 1 trạm đón riêng biệt (đảm bảo demand=1/trạm theo contract hiện tại).
    Số xe = ceil(n_bookings / 30) để không bao giờ vượt capacity.
    """
    # Depot
    depot = Location(
        id=uuid.uuid4(),
        name="ĐH Cần Thơ (Depot)",
        latitude=10.0302,
        longitude=105.7721,
    )
    db.add(depot)

    # Pickup locations — mỗi booking 1 trạm riêng
    pickup_locs = []
    for i in range(n_bookings):
        loc = Location(
            id=uuid.uuid4(),
            name=f"Trạm đón {i+1}",
            latitude=10.0302 + (i + 1) * 0.0015,
            longitude=105.7721 + (i + 1) * 0.0015,
            demand=1,
            time_window_start=datetime.datetime.combine(
                service_date, datetime.time(6, 0)
            ),
            time_window_end=datetime.datetime.combine(
                service_date, datetime.time(7, 30)
            ),
        )
        pickup_locs.append(loc)
        db.add(loc)

    # Drivers + Vehicles: mỗi xe capacity=30, tạo đủ xe để chứa hết
    import math
    n_vehicles = math.ceil(n_bookings / 30)
    vehicles = []
    for v in range(n_vehicles):
        driver = Profile(
            id=uuid.uuid4(),
            role=ProfileRole.DRIVER,
            full_name=f"Tài xế {v+1}",
        )
        db.add(driver)
        db.flush()
        vehicle = Vehicle(
            id=uuid.uuid4(),
            license_plate=f"65B-DAY6.{v+1:02d}",
            capacity=30,
            driver_id=driver.id,
        )
        db.add(vehicle)
        vehicles.append(vehicle)

    db.flush()

    # Students + Tickets (RESERVED)
    tickets = []
    for i, loc in enumerate(pickup_locs):
        student = Profile(
            id=uuid.uuid4(),
            role=ProfileRole.PASSENGER,
            full_name=f"Sinh viên D6-{i+1}",
        )
        db.add(student)
        db.flush()
        ticket = Ticket(
            id=uuid.uuid4(),
            user_id=student.id,
            service_date=service_date,
            session_id="MORNING_1",
            trip_type="pickup",
            pickup_location_id=loc.id,
            qr_code=f"QR_D6_N{n_bookings}_{i+1}_{uuid.uuid4().hex[:6].upper()}",
            status=TicketStatus.RESERVED,
        )
        tickets.append(ticket)
        db.add(ticket)

    db.commit()

    return {
        "depot": depot,
        "tickets": tickets,
        "vehicles": vehicles,
        "service_date": service_date,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: Rerun job 2 lần → Route/RouteStop không tăng thêm (idempotency)
# ─────────────────────────────────────────────────────────────────────────────
def test_rerun_job_does_not_create_duplicate_routes(db_session: Session):
    """
    Xác nhận idempotency khi rerun:
    - Lần 1: gọi run_route_job_worker → job SUCCEEDED, tạo N Route/RouteStop.
    - Lần 2: gọi lại cùng job_id → worker trả về ngay (guard SUCCEEDED),
             số Route và RouteStop KHÔNG tăng thêm.

    Cơ chế hiện tại trong route_worker.py:
        if job.status == RouteJobStatus.SUCCEEDED:
            return job   ← trả về sớm, không làm gì
    → Test này xác nhận guard đó hoạt động đúng end-to-end.
    """
    db = db_session
    service_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()
    data = _seed_scenario(db, n_bookings=4, service_date=service_date)

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=data["service_date"],
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=data["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    # ── Lần chạy 1 ───────────────────────────────────────────────────────────
    result_1 = run_route_job_worker(db=db, job_id=job.id)
    assert result_1.status == RouteJobStatus.SUCCEEDED, (
        f"Lần 1: Job phải SUCCEEDED, thực tế: {result_1.status} — {result_1.error_message}"
    )

    route_count_after_run1 = (
        db.query(Route).filter(Route.route_job_id == job.id).count()
    )
    stop_count_after_run1 = (
        db.query(RouteStop)
        .join(Route, Route.id == RouteStop.route_id)
        .filter(Route.route_job_id == job.id)
        .count()
    )
    assert route_count_after_run1 >= 1, "Sau lần 1 phải có ít nhất 1 Route"
    assert stop_count_after_run1 >= 2, "Sau lần 1 phải có ít nhất 1 depot + 1 pickup stop"

    print(
        f"\n  [Rerun] Run 1: {route_count_after_run1} Route(s), "
        f"{stop_count_after_run1} RouteStop(s)"
    )

    # ── Lần chạy 2 (cùng job_id, job đã SUCCEEDED) ───────────────────────────
    result_2 = run_route_job_worker(db=db, job_id=job.id)
    assert result_2.status == RouteJobStatus.SUCCEEDED, (
        "Run 2: Worker must return SUCCEEDED without raising exception"
    )

    route_count_after_run2 = (
        db.query(Route).filter(Route.route_job_id == job.id).count()
    )
    stop_count_after_run2 = (
        db.query(RouteStop)
        .join(Route, Route.id == RouteStop.route_id)
        .filter(Route.route_job_id == job.id)
        .count()
    )

    print(
        f"  [Rerun] Run 2: {route_count_after_run2} Route(s), "
        f"{stop_count_after_run2} RouteStop(s)"
    )

    assert route_count_after_run2 == route_count_after_run1, (
        f"IDEMPOTENCY FAIL: Run 2 created extra Route(s)! "
        f"Run1={route_count_after_run1}, Run2={route_count_after_run2}"
    )
    assert stop_count_after_run2 == stop_count_after_run1, (
        f"IDEMPOTENCY FAIL: Run 2 created extra RouteStop(s)! "
        f"Run1={stop_count_after_run1}, Run2={stop_count_after_run2}"
    )

    # Tickets must remain ASSIGNED after rerun (not reset)
    for tk in data["tickets"]:
        db.refresh(tk)
        assert tk.status == TicketStatus.ASSIGNED, (
            f"Ticket {tk.id} was reset after rerun -- must stay ASSIGNED"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: Benchmark thời gian chạy end-to-end worker (đo, không assert cứng)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("n_bookings", [5, 15, 30])
def test_worker_e2e_benchmark_timing(db_session: Session, n_bookings: int):
    """
    Đo thời gian toàn bộ pipeline run_route_job_worker:
        Đọc DB (Ticket, Location, Vehicle) → Sweep Clustering → Tabu Search → Ghi DB

    Khác với test_scaling_10_20_50_stops trong test_vrptw.py:
      - test_vrptw.py chỉ đo RIÊNG phần solver (VRPTWSolverService.solve), không có DB I/O.
      - Test này đo CẢ pipeline end-to-end bao gồm SQLAlchemy read/write.

    Kết quả được in để ghi vào runbook Ngày 8 (bàn giao scheduler).
    Không assert ngưỡng cứng — mục đích hôm nay là GHI NHẬN số liệu mẫu.
    """
    db = db_session
    # Dùng ngày khác nhau cho mỗi n_bookings để fixture cô lập hoàn toàn
    offset = {5: 3, 15: 4, 30: 5}.get(n_bookings, 6)
    service_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=offset)).date()

    data = _seed_scenario(db, n_bookings=n_bookings, service_date=service_date)

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=data["service_date"],
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=data["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    # ── Đo thời gian ─────────────────────────────────────────────────────────
    t_start = time.perf_counter()
    result = run_route_job_worker(db=db, job_id=job.id)
    elapsed = time.perf_counter() - t_start

    # Worker phải thành công — nếu FAIL thì seed/solver có vấn đề, không phải benchmark
    assert result.status == RouteJobStatus.SUCCEEDED, (
        f"Benchmark N={n_bookings}: Worker phải SUCCEEDED trước khi đo thời gian. "
        f"Lỗi: {result.error_message}"
    )

    route_count = db.query(Route).filter(Route.route_job_id == job.id).count()
    assigned_tickets = (
        db.query(Ticket)
        .filter(
            Ticket.service_date == data["service_date"],
            Ticket.session_id == "MORNING_1",
            Ticket.status == TicketStatus.ASSIGNED,
        )
        .count()
    )

    # ── In kết quả benchmark ─────────────────────────────────────────────────
    print(
        f"\n  [Benchmark] Worker E2E (N={n_bookings} bookings): "
        f"{elapsed:.3f}s | "
        f"{route_count} route(s) | "
        f"{assigned_tickets} tickets ASSIGNED"
    )

    # Kiểm tra tính đúng đắn cơ bản (không phải performance assert)
    assert route_count >= 1, f"N={n_bookings}: Phải có ít nhất 1 Route sau khi SUCCEEDED"
    assert assigned_tickets == n_bookings, (
        f"N={n_bookings}: Phải gán đúng {n_bookings} vé, "
        f"thực tế chỉ ASSIGNED {assigned_tickets}"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Ket qua benchmark mau -- Day 6 (2026-09-03, SQLite in-memory, static matrix)
#
#   N= 5 bookings:  0.394s  | 1 route  | 5  tickets ASSIGNED
#   N=15 bookings: 10.396s  | 1 route  | 15 tickets ASSIGNED
#   N=30 bookings: 92.749s  | 1 route  | 30 tickets ASSIGNED
#
# Mo truong: SQLite in-memory, static distance matrix (bypass OSRM), Python 3.12
# So sanh voi test_vrptw.py::test_scaling_10_20_50_stops (chi do rieng solver):
#   10 stops (50 iter): < 5s -- solver only
#   20 stops (30 iter): < 12s -- solver only
#   50 stops (10 iter): < 30s -- solver only
#
# Nhan xet: DB I/O (SQLAlchemy read/write SQLite) them ~0.1-0.5s overhead.
# Bottleneck chinh la Tabu Search O(n^2) -- N=30 mat 92s la do so vong lap.
# Tren Render/Supabase PostgreSQL: du kien cao hon do network latency DB (~+1-3s).
# Day 8 (ban giao scheduler): dung N=30 -> 92s lam UPPER BOUND SLA.
# ─────────────────────────────────────────────────────────────────────────────
