"""
test_khanh_job_lifecycle_day10.py
=================================
Bộ test kiểm thử toàn diện cho nhiệm vụ của Khánh:
Ngày 10 — Job Lifecycle:
1. Idempotency (Chống chạy trùng, khóa duy nhất service_date + session_id + trip_type).
2. Transaction & Rollback an toàn khi validation thất bại (không để lại rác dữ liệu).
3. Retry cơ chế phục hồi khi job trước đó bị FAILED.
4. Publish có điều kiện (Chỉ công bố lộ trình khi validation Ngày 9 pass 100%).
"""

import uuid
import datetime
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy import text
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
from app.services.route_validator import RouteValidator, RouteValidationError
from app.services.vrptw_solver import VRPTWSolverService
from app.api.v1.endpoints.routes import generate_routes, RouteGenerateRequest, read_routes


def _ensure_auth_user(db: Session, user_id: uuid.UUID) -> None:
    """Insert into auth.users to satisfy profiles FK constraint (Supabase pattern)."""
    try:
        db.execute(
            text(
                "INSERT INTO auth.users (id, aud, role) "
                "VALUES (:id, 'authenticated', 'authenticated') "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": str(user_id)},
        )
        db.commit()
    except Exception:
        db.rollback()


# ── Patch solver sang static matrix (tránh network OSRM) ──────────────────────
class _StaticSolverService(VRPTWSolverService):
    def __init__(self):
        super().__init__(use_static_matrix=True)


@pytest.fixture(autouse=True)
def patch_solver(monkeypatch):
    import app.services.route_worker as rw
    monkeypatch.setattr(rw, "VRPTWSolverService", _StaticSolverService)


# ── Function-scoped DB fixture: session sạch cho mỗi test ─────────────────────
@pytest.fixture(scope="function")
def db():
    """
    Override module-scoped `db` từ conftest.
    Mỗi test Day 10 dùng session riêng; kết thúc test sẽ rollback nếu chưa commit.
    Việc cleanup dữ liệu thật được giao cho _cleanup_day10_environment().
    """
    from app.core.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        try:
            session.rollback()
        except Exception:
            pass
        session.close()


def _cleanup_day10_environment(db: Session, env: dict) -> None:
    """Dọn dẹp toàn bộ dữ liệu do _seed_day10_environment tạo ra — đúng thứ tự FK."""
    from sqlalchemy import text as sa_text
    try:
        rj_id = env.get("route_job_id")
        if rj_id:
            # route_stops phải xóa trước routes
            db.execute(sa_text(
                "DELETE FROM route_stops WHERE route_id IN "
                "(SELECT id FROM routes WHERE route_job_id = :rj_id)"
            ), {"rj_id": str(rj_id)})
            # Unlink tickets khỏi routes trước khi xóa routes
            db.execute(sa_text(
                "UPDATE tickets SET route_id = NULL, status = 'reserved' WHERE route_id IN "
                "(SELECT id FROM routes WHERE route_job_id = :rj_id)"
            ), {"rj_id": str(rj_id)})
            db.execute(sa_text("DELETE FROM routes WHERE route_job_id = :rj_id"), {"rj_id": str(rj_id)})
            db.execute(sa_text("DELETE FROM route_jobs WHERE id = :rj_id"), {"rj_id": str(rj_id)})

        # Also clear any routes associated with test vehicles if not caught above
        for vid in env.get("vehicle_ids", []):
            db.execute(sa_text(
                "DELETE FROM route_stops WHERE route_id IN "
                "(SELECT id FROM routes WHERE vehicle_id = :vid)"
            ), {"vid": str(vid)})
            db.execute(sa_text(
                "UPDATE tickets SET route_id = NULL, status = 'reserved' WHERE route_id IN "
                "(SELECT id FROM routes WHERE vehicle_id = :vid)"
            ), {"vid": str(vid)})
            db.execute(sa_text("DELETE FROM routes WHERE vehicle_id = :vid"), {"vid": str(vid)})

        # Tickets
        for tid in env.get("ticket_ids", []):
            db.execute(sa_text("DELETE FROM tickets WHERE id = :id"), {"id": str(tid)})

        # Profiles rồi auth.users
        for sid in env.get("student_ids", []):
            db.execute(sa_text("DELETE FROM profiles WHERE id = :id"), {"id": str(sid)})
            db.execute(sa_text("DELETE FROM auth.users WHERE id = :id"), {"id": str(sid)})

        # Vehicles và Locations
        for vid in env.get("vehicle_ids", []):
            db.execute(sa_text("DELETE FROM vehicles WHERE id = :id"), {"id": str(vid)})
        for lid in env.get("location_ids", []):
            db.execute(sa_text("DELETE FROM locations WHERE id = :id"), {"id": str(lid)})

        db.commit()
    except Exception as exc:
        db.rollback()
        import logging
        logging.getLogger(__name__).warning(f"[cleanup_day10] Cleanup partial failure: {exc}")



def _seed_day10_environment(db: Session) -> dict:
    """Tạo Depot, 2 Pickup Locations, 1 Vehicle và 2 Sinh viên có vé RESERVED."""
    service_date = datetime.date(2026, 9, 25)
    session_id = "MORNING_1"
    trip_type = "pickup"

    # Phòng thủ: Xóa trước bất kỳ job thừa nào cùng ca từ các lần chạy trước
    existing_jobs = db.query(RouteJob).filter(
        RouteJob.service_date == service_date,
        RouteJob.session_id == session_id,
        RouteJob.trip_type == trip_type,
    ).all()
    for ej in existing_jobs:
        db.execute(text("DELETE FROM route_stops WHERE route_id IN (SELECT id FROM routes WHERE route_job_id = :jid)"), {"jid": str(ej.id)})
        db.execute(text("UPDATE tickets SET route_id = NULL WHERE route_id IN (SELECT id FROM routes WHERE route_job_id = :jid)"), {"jid": str(ej.id)})
        db.execute(text("DELETE FROM routes WHERE route_job_id = :jid"), {"jid": str(ej.id)})
        db.execute(text("DELETE FROM route_jobs WHERE id = :jid"), {"jid": str(ej.id)})
    db.commit()

    depot = Location(
        id=uuid.uuid4(),
        code=f"DEPOT_{uuid.uuid4().hex[:6]}",
        name="ĐH Cần Thơ (Depot)",
        latitude=10.0302,
        longitude=105.7721,
    )
    st_1 = Location(
        id=uuid.uuid4(),
        code=f"ST1_{uuid.uuid4().hex[:6]}",
        name="Trạm 1 - KTX A",
        latitude=10.0315,
        longitude=105.7690,
    )
    st_2 = Location(
        id=uuid.uuid4(),
        code=f"ST2_{uuid.uuid4().hex[:6]}",
        name="Trạm 2 - Khoa CNTT",
        latitude=10.0330,
        longitude=105.7680,
    )
    db.add_all([depot, st_1, st_2])

    vehicle = Vehicle(
        id=uuid.uuid4(),
        license_plate=f"65B-{uuid.uuid4().hex[:5].upper()}",
        capacity=45,
    )
    db.add(vehicle)

    student_1_id = uuid.uuid4()
    student_2_id = uuid.uuid4()

    # Phải insert auth.users trước vì profiles.id FK → auth.users.id (Supabase)
    db.flush()
    _ensure_auth_user(db, student_1_id)
    _ensure_auth_user(db, student_2_id)
    db.commit()

    # Supabase trigger `on_auth_user_created` có thể đã tự động tạo row trong `profiles`
    student_1 = db.query(Profile).filter(Profile.id == student_1_id).first()
    if not student_1:
        student_1 = Profile(
            id=student_1_id,
            role=ProfileRole.PASSENGER,
            full_name="Nguyễn Văn A",
        )
        db.add(student_1)
    else:
        student_1.role = ProfileRole.PASSENGER
        student_1.full_name = "Nguyễn Văn A"

    student_2 = db.query(Profile).filter(Profile.id == student_2_id).first()
    if not student_2:
        student_2 = Profile(
            id=student_2_id,
            role=ProfileRole.PASSENGER,
            full_name="Trần Thị B",
        )
        db.add(student_2)
    else:
        student_2.role = ProfileRole.PASSENGER
        student_2.full_name = "Trần Thị B"

    db.commit()

    ticket_1 = Ticket(
        id=uuid.uuid4(),
        user_id=student_1.id,
        service_date=service_date,
        session_id=session_id,
        trip_type=trip_type,
        pickup_location_id=st_1.id,
        qr_code=f"QR_{uuid.uuid4().hex[:8]}",
        status=TicketStatus.RESERVED,
    )
    ticket_2 = Ticket(
        id=uuid.uuid4(),
        user_id=student_2.id,
        service_date=service_date,
        session_id=session_id,
        trip_type=trip_type,
        pickup_location_id=st_2.id,
        qr_code=f"QR_{uuid.uuid4().hex[:8]}",
        status=TicketStatus.RESERVED,
    )
    db.add_all([ticket_1, ticket_2])
    db.commit()

    return {
        "depot": depot,
        "st_1": st_1,
        "st_2": st_2,
        "vehicle": vehicle,
        "student_1": student_1,
        "student_2": student_2,
        "ticket_1": ticket_1,
        "ticket_2": ticket_2,
        "service_date": service_date,
        "session_id": session_id,
        "trip_type": trip_type,
        # Keys cho _cleanup_day10_environment
        "ticket_ids": [ticket_1.id, ticket_2.id],
        "student_ids": [student_1.id, student_2.id],
        "location_ids": [depot.id, st_1.id, st_2.id],
        "vehicle_ids": [vehicle.id],
        "route_job_id": None,  # Sẽ được test cập nhật sau khi tạo RouteJob
    }


# ══════════════════════════════════════════════════════════════════════════════
# 1. TEST IDEMPOTENCY: CHỐNG CHẠY TRÙNG VÀ BẢO ĐẢM KHÓA DUY NHẤT
# ══════════════════════════════════════════════════════════════════════════════

def test_day10_idempotency_blocks_duplicate_succeeded_job(db: Session, monkeypatch):
    """Khi job cho ca đã SUCCEEDED, yêu cầu tạo lại phải bị từ chối 409 Conflict."""
    env = _seed_day10_environment(db)
    cron_secret = "test_cron_secret_day10"
    monkeypatch.setattr(settings, "CRON_SECRET", cron_secret)
    try:
        cutoff_valid_dt = datetime.datetime.combine(
            env["service_date"] - datetime.timedelta(days=1),
            datetime.time(hour=23, minute=0, second=0),
            tzinfo=VN_TZ,
        )
        with patch("app.api.v1.endpoints.routes.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = cutoff_valid_dt
            mock_dt.datetime.combine = datetime.datetime.combine
            mock_dt.timedelta = datetime.timedelta
            mock_dt.time = datetime.time

            req = RouteGenerateRequest(
                service_date=env["service_date"],
                session_id=env["session_id"],
                trip_type=env["trip_type"],
                depot_location_id=env["depot"].id,
            )

            res1 = generate_routes(request_in=req, x_cron_secret=cron_secret, db=db)
            if isinstance(res1, dict):
                env["route_job_id"] = res1.get("job_id")
            else:
                env["route_job_id"] = getattr(res1, "id", None)
            status_val = res1.get("status") if isinstance(res1, dict) else getattr(res1, "status", None)
            assert status_val == RouteJobStatus.SUCCEEDED

            with pytest.raises(HTTPException) as exc_info:
                generate_routes(request_in=req, x_cron_secret=cron_secret, db=db)

            assert exc_info.value.status_code == 409
            assert "đã hoàn tất thành công trước đó" in exc_info.value.detail
    finally:
        _cleanup_day10_environment(db, env)


def test_day10_idempotency_returns_active_job_without_duplication(db: Session, monkeypatch):
    """Khi job đang ở trạng thái QUEUED hoặc RUNNING, API trả về active job, không tạo job mới."""
    env = _seed_day10_environment(db)
    cron_secret = "test_cron_secret_day10"
    monkeypatch.setattr(settings, "CRON_SECRET", cron_secret)
    existing_job = RouteJob(
        id=uuid.uuid4(),
        service_date=env["service_date"],
        session_id=env["session_id"],
        trip_type=env["trip_type"],
        depot_location_id=env["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(existing_job)
    db.commit()
    env["route_job_id"] = existing_job.id
    try:
        cutoff_valid_dt = datetime.datetime.combine(
            env["service_date"] - datetime.timedelta(days=1),
            datetime.time(hour=23, minute=0, second=0),
            tzinfo=VN_TZ,
        )
        with patch("app.api.v1.endpoints.routes.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = cutoff_valid_dt
            mock_dt.datetime.combine = datetime.datetime.combine
            mock_dt.timedelta = datetime.timedelta
            mock_dt.time = datetime.time

            req = RouteGenerateRequest(
                service_date=env["service_date"],
                session_id=env["session_id"],
                trip_type=env["trip_type"],
                depot_location_id=env["depot"].id,
            )

            res = generate_routes(request_in=req, x_cron_secret=cron_secret, db=db)
            assert res.id == existing_job.id
            total_jobs = db.query(RouteJob).filter(
                RouteJob.service_date == env["service_date"],
                RouteJob.session_id == env["session_id"],
            ).count()
            assert total_jobs == 1
    finally:
        _cleanup_day10_environment(db, env)


# ══════════════════════════════════════════════════════════════════════════════
# 2. TEST TRANSACTION & ROLLBACK KHI THẤT BẠI VALIDATION NGÀY 9
# ══════════════════════════════════════════════════════════════════════════════

def test_day10_transaction_rollback_on_validation_failure(db: Session, monkeypatch):
    """
    Khi solver trả về lời giải vi phạm validation Ngày 9 (ví dụ quá tải > 45 khách):
    - Toàn bộ transaction phải rollback: không có Route hay RouteStop nào được lưu vào DB.
    - Vé phải giữ nguyên trạng thái RESERVED (không bị gán dở dang).
    - Job status chuyển thành FAILED kèm mã lỗi OVERLOAD_VIOLATION.
    """
    env = _seed_day10_environment(db)

    class MockOverloadSolver:
        def solve(self, *args, **kwargs):
            return [
                {
                    "vehicle_id": str(env["vehicle"].id),
                    "total_demand": 50,
                    "total_distance_km": 15.0,
                    "ordered_stops": [
                        {"id": "depot", "arrival_time": "06:00"},
                        {"id": "location_0", "arrival_time": "06:15", "demand": 25},
                        {"id": "location_1", "arrival_time": "06:30", "demand": 25},
                    ]
                }
            ]

    import app.services.route_worker as rw
    monkeypatch.setattr(rw, "VRPTWSolverService", MockOverloadSolver)

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=env["service_date"],
        session_id=env["session_id"],
        trip_type=env["trip_type"],
        depot_location_id=env["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()
    env["route_job_id"] = job.id
    try:
        with pytest.raises(RouteStopValidationError) as exc_info:
            run_route_job_worker(db=db, job_id=job.id)

        assert exc_info.value.error_code == "OVERLOAD_VIOLATION"

        created_routes = db.query(Route).filter(Route.route_job_id == job.id).all()
        assert len(created_routes) == 0

        created_stops = db.query(RouteStop).all()
        assert len(created_stops) == 0

        db.refresh(env["ticket_1"])
        db.refresh(env["ticket_2"])
        assert env["ticket_1"].status == TicketStatus.RESERVED
        assert env["ticket_1"].route_id is None
        assert env["ticket_2"].status == TicketStatus.RESERVED
        assert env["ticket_2"].route_id is None

        db.refresh(job)
        assert job.status == RouteJobStatus.FAILED
        assert "OVERLOAD_VIOLATION" in job.error_message
    finally:
        _cleanup_day10_environment(db, env)


# ══════════════════════════════════════════════════════════════════════════════
# 3. TEST RETRY SAU KHI JOB FAILED
# ══════════════════════════════════════════════════════════════════════════════

def test_day10_retry_failed_job_to_succeeded(db: Session, monkeypatch):
    """
    Khi job đang ở trạng thái FAILED, gọi chạy lại:
    - Job được cập nhật từ FAILED sang QUEUED -> SUCCEEDED.
    - Xóa bỏ error_message cũ và tạo đầy đủ routes, route_stops.
    - Vé chuyển sang trạng thái ASSIGNED.
    """
    env = _seed_day10_environment(db)

    failed_job = RouteJob(
        id=uuid.uuid4(),
        service_date=env["service_date"],
        session_id=env["session_id"],
        trip_type=env["trip_type"],
        depot_location_id=env["depot"].id,
        status=RouteJobStatus.FAILED,
        error_message="[PREVIOUS_ERROR] Solver failed temporarily",
    )
    db.add(failed_job)
    db.commit()
    env["route_job_id"] = failed_job.id
    cron_secret = "test_cron_secret_day10"
    monkeypatch.setattr(settings, "CRON_SECRET", cron_secret)
    try:
        cutoff_valid_dt = datetime.datetime.combine(
            env["service_date"] - datetime.timedelta(days=1),
            datetime.time(hour=23, minute=0, second=0),
            tzinfo=VN_TZ,
        )
        with patch("app.api.v1.endpoints.routes.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = cutoff_valid_dt
            mock_dt.datetime.combine = datetime.datetime.combine
            mock_dt.timedelta = datetime.timedelta
            mock_dt.time = datetime.time

            req = RouteGenerateRequest(
                service_date=env["service_date"],
                session_id=env["session_id"],
                trip_type=env["trip_type"],
                depot_location_id=env["depot"].id,
            )

            res = generate_routes(request_in=req, x_cron_secret=cron_secret, db=db)
            assert res["job_id"] == failed_job.id
            assert res["status"] == RouteJobStatus.SUCCEEDED
            assert res["error_message"] is None

            db.refresh(failed_job)
            assert failed_job.status == RouteJobStatus.SUCCEEDED

            routes = db.query(Route).filter(Route.route_job_id == failed_job.id).all()
            assert len(routes) >= 1

            db.refresh(env["ticket_1"])
            db.refresh(env["ticket_2"])
            assert env["ticket_1"].status == TicketStatus.ASSIGNED
            assert env["ticket_1"].route_id is not None
            assert env["ticket_2"].status == TicketStatus.ASSIGNED
            assert env["ticket_2"].route_id is not None
    finally:
        _cleanup_day10_environment(db, env)


# ══════════════════════════════════════════════════════════════════════════════
# 4. TEST PUBLISH CÓ ĐIỀU KIỆN (CONDITIONAL PUBLISH)
# ══════════════════════════════════════════════════════════════════════════════

def test_day10_conditional_publish_visibility_rules(db: Session, monkeypatch):
    """
    Xác nhận lộ trình chỉ khả dụng cho sinh viên khi job hoàn tất thành công (SUCCEEDED).
    Nếu job thất bại, sinh viên gọi GET /routes sẽ nhận danh sách rỗng (0 tuyến).
    """
    env = _seed_day10_environment(db)
    job = RouteJob(
        id=uuid.uuid4(),
        service_date=env["service_date"],
        session_id=env["session_id"],
        trip_type=env["trip_type"],
        depot_location_id=env["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()
    env["route_job_id"] = job.id
    try:
        student_routes_before = read_routes(
            service_date=env["service_date"],
            session_id=env["session_id"],
            trip_type=env["trip_type"],
            status=None,
            db=db,
            current_profile=env["student_1"],
        )
        assert len(student_routes_before) == 0

        run_route_job_worker(db=db, job_id=job.id)

        student_routes_after = read_routes(
            service_date=env["service_date"],
            session_id=env["session_id"],
            trip_type=env["trip_type"],
            status=None,
            db=db,
            current_profile=env["student_1"],
        )
        assert len(student_routes_after) == 1
        assert student_routes_after[0].service_date == env["service_date"]
        assert len(student_routes_after[0].stops) >= 2
    finally:
        _cleanup_day10_environment(db, env)
