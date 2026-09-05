"""
test_day7_failure_retry_deadline.py — Thành viên 3 (Duy - Routing/Scheduler) — Ngày T7

Nhiệm vụ T7 (đúng theo Implementation Plan 1-2 weeks & team task assignments):
  1. Xử lý failure / retry job:
     - test_route_job_failure_no_reserved_tickets: Job thất bại khi không có vé RESERVED,
       rollback transaction, cập nhật job.status = FAILED, lưu error_message.
     - test_route_job_failure_invalid_depot: Job thất bại khi depot_location_id không tồn tại,
       cập nhật status FAILED và error_message.
     - test_route_job_retry_failed_to_succeeded: Chạy lại (retry) một job đã FAILED
       sau khi đã bổ sung vé hợp lệ -> chuyển từ FAILED -> RUNNING -> SUCCEEDED,
       tạo Route/RouteStop và xóa error_message.
     - test_route_job_retry_via_api_endpoint: Gọi API POST /api/v1/routes/generate khi job
       trước đó đã FAILED -> API tự động retry trên job_id đó và trả về SUCCEEDED.

  2. Test mốc deadline 21:59 vs 22:01 (Asia/Ho_Chi_Minh timezone):
     - test_deadline_21_59_vs_22_01_boundary_checks:
       - Với ngày chạy D = 2026-09-10 (Cutoff D-1 22:00 = 2026-09-09 22:00:00 ICT):
       - Tại 21:59:59 ngày D-1 (trước deadline): Đặt vé thành công, Sinh tuyến bị từ chối (400 Bad Request).
       - Tại 22:01:00 ngày D-1 (sau deadline): Đặt vé bị từ chối (400 Bad Request), Sinh tuyến được phép.
"""
import uuid
import datetime
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import VN_TZ
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.services.route_worker import run_route_job_worker, RouteStopValidationError
from app.services.vrptw_solver import VRPTWSolverService
from app.api.v1.endpoints.tickets import validate_booking_deadline
from app.api.v1.endpoints.routes import generate_routes, RouteGenerateRequest


# ── Patch solver sang static matrix (bypass OSRM / network calls) ───────────
class _StaticSolverService(VRPTWSolverService):
    def __init__(self):
        super().__init__(use_static_matrix=True)


@pytest.fixture(autouse=True)
def patch_solver(monkeypatch):
    import app.services.route_worker as rw
    monkeypatch.setattr(rw, "VRPTWSolverService", _StaticSolverService)


# ── Subclass datetime để mock now() chuẩn xác mà không hỏng combine() ───────
class MockDatetime(datetime.datetime):
    _target_now: datetime.datetime = None

    @classmethod
    def now(cls, tz=None):
        if cls._target_now is not None:
            if tz is not None and cls._target_now.tzinfo is not None:
                return cls._target_now.astimezone(tz)
            return cls._target_now
        return super().now(tz=tz)


# ── Helper seed base data ────────────────────────────────────────────────────
def _seed_base_environment(db: Session) -> dict:
    """Tạo 1 Depot, 2 Pickup Locations, 1 Vehicle và 2 SV test."""
    depot = Location(
        id=uuid.uuid4(),
        name="ĐH Cần Thơ (Depot)",
        latitude=10.0302,
        longitude=105.7721,
    )
    pickup_1 = Location(
        id=uuid.uuid4(),
        name="Trạm 1 - KTX A",
        latitude=10.0315,
        longitude=105.7690,
    )
    pickup_2 = Location(
        id=uuid.uuid4(),
        name="Trạm 2 - Khoa CNTT",
        latitude=10.0330,
        longitude=105.7680,
    )
    db.add_all([depot, pickup_1, pickup_2])

    vehicle = Vehicle(
        id=uuid.uuid4(),
        license_plate="65A-999.99",
        capacity=30,
        driver_id=None,
    )
    db.add(vehicle)

    student1 = Profile(
        id=uuid.uuid4(),
        full_name="Sinh Viên 1 Day 7",
        role=ProfileRole.PASSENGER,
    )
    student2 = Profile(
        id=uuid.uuid4(),
        full_name="Sinh Viên 2 Day 7",
        role=ProfileRole.PASSENGER,
    )
    db.add_all([student1, student2])
    db.commit()

    return {
        "depot_id": depot.id,
        "pickup_1_id": pickup_1.id,
        "pickup_2_id": pickup_2.id,
        "vehicle_id": vehicle.id,
        "student1_id": student1.id,
        "student2_id": student2.id,
    }


# =============================================================================
# 1. TEST JOB FAILURE HANDLING & TRANSACTION SAFETY
# =============================================================================

def test_route_job_failure_no_reserved_tickets(db_session):
    """
    Kiểm tra khi chạy job nhưng không có vé RESERVED nào:
    - Worker ném ngoại lệ RouteStopValidationError.
    - Status của job chuyển sang FAILED.
    - error_message được lưu vào DB.
    - Không có Route hay RouteStop nào được tạo.
    """
    db = db_session
    base = _seed_base_environment(db)
    service_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()

    # Tạo Job nhưng KHÔNG tạo ticket nào
    job = RouteJob(
        id=uuid.uuid4(),
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=base["depot_id"],
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    # Thực thi worker -> Phải ném ngoại lệ
    with pytest.raises(Exception):
        run_route_job_worker(db=db, job_id=job.id)

    db.refresh(job)
    assert job.status == RouteJobStatus.FAILED
    assert "DATABASE_WRITE_FAILED" in job.error_message or "No RESERVED tickets found" in job.error_message

    # Kiểm tra không sinh Route nào
    route_count = db.query(Route).filter(Route.route_job_id == job.id).count()
    assert route_count == 0


def test_route_job_failure_invalid_depot(db_session):
    """
    Kiểm tra khi job có depot_location_id không tồn tại trong DB:
    - Worker thất bại, cập nhật status FAILED và error_message.
    """
    db = db_session
    base = _seed_base_environment(db)
    service_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()

    invalid_depot_id = uuid.uuid4()
    job = RouteJob(
        id=uuid.uuid4(),
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=invalid_depot_id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    with pytest.raises(ValueError):
        run_route_job_worker(db=db, job_id=job.id)

    db.refresh(job)
    assert job.status == RouteJobStatus.FAILED
    assert f"Depot {invalid_depot_id}" in job.error_message


# =============================================================================
# 2. TEST JOB RETRY LOGIC (FAILED -> SUCCEEDED)
# =============================================================================

def test_route_job_retry_failed_to_succeeded(db_session):
    """
    Kiểm tra luồng Retry của worker:
    1. Chạy job khi chưa có vé -> FAILED.
    2. Thêm vé hợp lệ cho ca/chiều đó.
    3. Thử lại (retry) bằng cách gọi lại run_route_job_worker(db, job.id).
    4. Xác nhận status từ FAILED -> SUCCEEDED, error_message = None,
       Route/RouteStop được tạo đúng và vé chuyển sang ASSIGNED.
    """
    db = db_session
    base = _seed_base_environment(db)
    service_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=base["depot_id"],
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    # 1. Lần 1: Chạy worker khi 0 vé -> FAILED
    with pytest.raises(Exception):
        run_route_job_worker(db=db, job_id=job.id)

    db.refresh(job)
    assert job.status == RouteJobStatus.FAILED
    assert job.error_message is not None

    # 2. Bổ sung 2 vé RESERVED
    ticket1 = Ticket(
        id=uuid.uuid4(),
        user_id=base["student1_id"],
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=base["pickup_1_id"],
        qr_code="QR_RETRY_001",
        status=TicketStatus.RESERVED,
    )
    ticket2 = Ticket(
        id=uuid.uuid4(),
        user_id=base["student2_id"],
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=base["pickup_2_id"],
        qr_code="QR_RETRY_002",
        status=TicketStatus.RESERVED,
    )
    db.add_all([ticket1, ticket2])
    db.commit()

    # 3. Lần 2: Retry job_id cũ
    retry_result = run_route_job_worker(db=db, job_id=job.id)

    # 4. Kiểm tra kết quả sau retry
    assert retry_result.status == RouteJobStatus.SUCCEEDED
    assert retry_result.error_message is None

    routes = db.query(Route).filter(Route.route_job_id == job.id).all()
    assert len(routes) > 0

    db.refresh(ticket1)
    db.refresh(ticket2)
    assert ticket1.status == TicketStatus.ASSIGNED
    assert ticket2.status == TicketStatus.ASSIGNED


def test_route_job_retry_via_api_endpoint(db_session, monkeypatch):
    """
    Kiểm tra retry thông qua API POST /api/v1/routes/generate:
    1. Gọi generate khi chưa có vé -> API trả response với status FAILED.
    2. Bổ sung vé.
    3. Gọi lại generate cho cùng service_date + session_id + trip_type.
    4. API phát hiện job FAILED cũ, thực hiện retry và trả về status SUCCEEDED.
    """
    db = db_session
    base = _seed_base_environment(db)
    service_date = datetime.date(2026, 9, 10)
    d_minus_1_after_cutoff = datetime.datetime(2026, 9, 9, 22, 5, 0, tzinfo=VN_TZ)

    # Set mock CRON_SECRET cho API auth
    monkeypatch.setattr(settings, "CRON_SECRET", "test_cron_secret_key")

    req = RouteGenerateRequest(
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=base["depot_id"],
    )

    with patch("app.api.v1.endpoints.routes.datetime.datetime", MockDatetime):
        MockDatetime._target_now = d_minus_1_after_cutoff

        # 1. Lần 1: Gọi API generate -> FAILED (do 0 vé)
        res1 = generate_routes(
            request_in=req,
            x_cron_secret="test_cron_secret_key",
            db=db,
        )
        assert res1["status"] == RouteJobStatus.FAILED

        # 2. Thêm vé RESERVED
        ticket = Ticket(
            id=uuid.uuid4(),
            user_id=base["student1_id"],
            service_date=service_date,
            session_id="MORNING_1",
            trip_type="pickup",
            pickup_location_id=base["pickup_1_id"],
            qr_code="QR_API_RETRY_001",
            status=TicketStatus.RESERVED,
        )
        db.add(ticket)
        db.commit()

        # 3. Lần 2: Gọi lại API generate -> Retry thành công
        res2 = generate_routes(
            request_in=req,
            x_cron_secret="test_cron_secret_key",
            db=db,
        )
        assert res2["status"] == RouteJobStatus.SUCCEEDED
        assert res2["error_message"] is None
        assert res2["job_id"] == res1["job_id"]  # Đã retry đúng job_id cũ


# =============================================================================
# 3. TEST DEADLINE 21:59 VS 22:01 (ASIA/HO_CHI_MINH TIMEZONE)
# =============================================================================

def test_deadline_21_59_vs_22_01_boundary_checks(db_session, monkeypatch):
    """
    Kiểm tra ranh giới 21:59:59 (trước cutoff) vs 22:01:00 (sau cutoff) ngày D-1:
    Mốc dịch vụ: Ngày chạy D = 2026-09-10. Cutoff D-1 = 2026-09-09 22:00:00 ICT.

    - Tại 21:59:59 ngày D-1:
      + Đặt vé (validate_booking_deadline): CHO PHÉP (không ném lỗi).
      + Sinh tuyến (generate_routes): TỪ CHỐI (400 Bad Request, báo phải sau 22:00).

    - Tại 22:01:00 ngày D-1:
      + Đặt vé (validate_booking_deadline): TỪ CHỐI (400 Bad Request, quá hạn 22:00).
      + Sinh tuyến (generate_routes): CHO PHÉP (qua kiểm tra deadline).
    """
    db = db_session
    base = _seed_base_environment(db)
    monkeypatch.setattr(settings, "CRON_SECRET", "test_cron_secret_key")

    service_date = datetime.date(2026, 9, 10)
    d_minus_1 = service_date - datetime.timedelta(days=1)  # 2026-09-09

    time_21_59 = datetime.datetime.combine(
        d_minus_1, datetime.time(21, 59, 59), tzinfo=VN_TZ
    )
    time_22_01 = datetime.datetime.combine(
        d_minus_1, datetime.time(22, 1, 0), tzinfo=VN_TZ
    )

    req = RouteGenerateRequest(
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=base["depot_id"],
    )

    # ── MỐC 1: 21:59:59 ICT (TRƯỚC DEADLINE) ──────────────────────────────────
    with patch("app.api.v1.endpoints.tickets.datetime.datetime", MockDatetime), \
         patch("app.api.v1.endpoints.routes.datetime.datetime", MockDatetime):
        MockDatetime._target_now = time_21_59

        # 1. Đặt vé trước 22:00 -> CHO PHÉP
        try:
            validate_booking_deadline(service_date)
        except HTTPException:
            pytest.fail("validate_booking_deadline bị lỗi ở mốc 21:59:59 (đáng lẽ phải cho phép).")

        # 2. Sinh tuyến trước 22:00 -> TỪ CHỐI (HTTP 400)
        with pytest.raises(HTTPException) as exc_info:
            generate_routes(
                request_in=req,
                x_cron_secret="test_cron_secret_key",
                db=db,
            )
        assert exc_info.value.status_code == 400
        assert "Chỉ có thể chạy job sinh tuyến sau mốc deadline 22:00" in exc_info.value.detail

    # ── MỐC 2: 22:01:00 ICT (SAU DEADLINE) ────────────────────────────────────
    ticket = Ticket(
        id=uuid.uuid4(),
        user_id=base["student1_id"],
        service_date=service_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=base["pickup_1_id"],
        qr_code="QR_DEADLINE_001",
        status=TicketStatus.RESERVED,
    )
    db.add(ticket)
    db.commit()

    with patch("app.api.v1.endpoints.tickets.datetime.datetime", MockDatetime), \
         patch("app.api.v1.endpoints.routes.datetime.datetime", MockDatetime):
        MockDatetime._target_now = time_22_01

        # 1. Đặt vé sau 22:00 -> TỪ CHỐI (HTTP 400)
        with pytest.raises(HTTPException) as exc_info:
            validate_booking_deadline(service_date)
        assert exc_info.value.status_code == 400
        assert "Đã quá hạn đặt vé 22:00" in exc_info.value.detail

        # 2. Sinh tuyến sau 22:00 -> CHO PHÉP (Qua mốc deadline, tạo & chạy job)
        res = generate_routes(
            request_in=req,
            x_cron_secret="test_cron_secret_key",
            db=db,
        )
        assert res["status"] == RouteJobStatus.SUCCEEDED
