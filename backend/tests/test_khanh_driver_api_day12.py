"""
test_khanh_driver_api_day12.py
===============================
Bộ kiểm thử tự động cho nhiệm vụ của Khánh:
Ngày 12 — API & Phân quyền Tài Xế:
1. Tài xế bắt đầu ca chạy (POST/PATCH /api/v1/routes/{id}/start) -> Route.status chuyển sang IN_PROGRESS.
2. Tài xế kết thúc ca chạy (POST/PATCH /api/v1/routes/{id}/end) -> Route.status chuyển sang COMPLETED.
3. Chặn tài xế điều khiển tuyến xe không thuộc quyền quản lý của xe mình (403 Forbidden).
4. Tài xế quét mã QR (POST /api/v1/tickets/verify-qr) điểm danh hành khách -> Ticket chuyển sang USED.
5. Chặn quét lại vé đã qua điểm danh (400 Bad Request).
"""

import uuid
import datetime
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStatus
from app.schemas.ticket import QRVerifyRequest
from app.api.v1.endpoints.routes import start_route, end_route
from app.api.v1.endpoints.tickets import verify_ticket_qr


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


@pytest.fixture(scope="function")
def db():
    """Session sạch cho mỗi test; rollback nếu chưa commit."""
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


def _cleanup_env(db: Session, env: dict) -> None:
    """Dọn dẹp DB đúng thứ tự khóa ngoại."""
    from sqlalchemy import text as sa_text
    try:
        # Route stops
        for rid in env.get("route_ids", []):
            db.execute(sa_text("DELETE FROM route_stops WHERE route_id = :id"), {"id": str(rid)})
            db.execute(sa_text("UPDATE tickets SET route_id = NULL WHERE route_id = :id"), {"id": str(rid)})
            db.execute(sa_text("DELETE FROM routes WHERE id = :id"), {"id": str(rid)})

        # Tickets
        for tid in env.get("ticket_ids", []):
            db.execute(sa_text("DELETE FROM tickets WHERE id = :id"), {"id": str(tid)})

        # Vehicles trước khi xóa driver profiles (FK vehicle.driver_id)
        for vid in env.get("vehicle_ids", []):
            db.execute(sa_text("DELETE FROM vehicles WHERE id = :id"), {"id": str(vid)})

        # Profiles & auth.users
        for uid in env.get("user_ids", []):
            db.execute(sa_text("DELETE FROM profiles WHERE id = :id"), {"id": str(uid)})
            db.execute(sa_text("DELETE FROM auth.users WHERE id = :id"), {"id": str(uid)})

        # Locations
        for lid in env.get("location_ids", []):
            db.execute(sa_text("DELETE FROM locations WHERE id = :id"), {"id": str(lid)})

        db.commit()
    except Exception as exc:
        db.rollback()
        import logging
        logging.getLogger(__name__).warning(f"[cleanup_day12] Warning: {exc}")


def _seed_driver_env(db: Session) -> dict:
    """Tạo Tài xế chính, Tài xế phụ, Phương tiện và Tuyến xe."""
    driver_1_id = uuid.uuid4()
    driver_2_id = uuid.uuid4()
    student_id = uuid.uuid4()

    _ensure_auth_user(db, driver_1_id)
    _ensure_auth_user(db, driver_2_id)
    _ensure_auth_user(db, student_id)
    db.commit()

    # Bypass trigger `prevent_role_self_change` bằng service_role session
    db.execute(text("SET LOCAL request.jwt.claim.role = 'service_role'"))

    driver_1 = db.query(Profile).filter(Profile.id == driver_1_id).first()
    if not driver_1:
        driver_1 = Profile(id=driver_1_id, role=ProfileRole.DRIVER, full_name="Bác tài A")
        db.add(driver_1)
    else:
        driver_1.role = ProfileRole.DRIVER
        driver_1.full_name = "Bác tài A"

    driver_2 = db.query(Profile).filter(Profile.id == driver_2_id).first()
    if not driver_2:
        driver_2 = Profile(id=driver_2_id, role=ProfileRole.DRIVER, full_name="Bác tài B (Lạ)")
        db.add(driver_2)
    else:
        driver_2.role = ProfileRole.DRIVER
        driver_2.full_name = "Bác tài B (Lạ)"

    student = db.query(Profile).filter(Profile.id == student_id).first()
    if not student:
        student = Profile(id=student_id, role=ProfileRole.PASSENGER, full_name="Học sinh C")
        db.add(student)
    else:
        student.role = ProfileRole.PASSENGER
        student.full_name = "Học sinh C"

    db.commit()

    vehicle = Vehicle(
        id=uuid.uuid4(),
        license_plate=f"65B-{uuid.uuid4().hex[:5].upper()}",
        capacity=45,
        driver_id=driver_1.id,
    )
    db.add(vehicle)

    st = Location(
        id=uuid.uuid4(),
        code=f"ST_{uuid.uuid4().hex[:6]}",
        name="Trạm Đón Xe Buýt 1",
        latitude=10.0310,
        longitude=105.7680,
    )
    db.add(st)
    db.commit()

    service_date = datetime.date(2026, 10, 20)
    session_id = "MORNING_1"
    trip_type = "pickup"

    route = Route(
        id=uuid.uuid4(),
        service_date=service_date,
        session_id=session_id,
        trip_type=trip_type,
        vehicle_id=vehicle.id,
        status=RouteStatus.PENDING,
        total_distance=15.0,
    )
    db.add(route)
    db.commit()

    ticket = Ticket(
        id=uuid.uuid4(),
        user_id=student.id,
        route_id=route.id,
        service_date=service_date,
        session_id=session_id,
        trip_type=trip_type,
        pickup_location_id=st.id,
        qr_code=f"QR_{uuid.uuid4().hex[:12].upper()}",
        status=TicketStatus.ASSIGNED,
    )
    db.add(ticket)
    db.commit()

    return {
        "driver_1": driver_1,
        "driver_2": driver_2,
        "student": student,
        "vehicle": vehicle,
        "station": st,
        "route": route,
        "ticket": ticket,
        "user_ids": [driver_1_id, driver_2_id, student_id],
        "vehicle_ids": [vehicle.id],
        "location_ids": [st.id],
        "route_ids": [route.id],
        "ticket_ids": [ticket.id],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 1. TEST BẮT ĐẦU VÀ KẾT THÚC CA CHẠY TUYẾN
# ══════════════════════════════════════════════════════════════════════════════

def test_day12_driver_start_and_end_route_success(db: Session):
    """Tài xế quản lý xe có thể bắt đầu ca (IN_PROGRESS) và kết thúc ca (COMPLETED)."""
    env = _seed_driver_env(db)
    try:
        route = env["route"]
        driver = env["driver_1"]

        # 1. Bắt đầu ca chạy
        started = start_route(route_id=route.id, db=db, current_driver=driver)
        assert started.status == RouteStatus.IN_PROGRESS

        db.refresh(route)
        assert route.status == RouteStatus.IN_PROGRESS

        # 2. Kết thúc ca chạy
        ended = end_route(route_id=route.id, db=db, current_driver=driver)
        assert ended.status == RouteStatus.COMPLETED

        db.refresh(route)
        assert route.status == RouteStatus.COMPLETED
    finally:
        _cleanup_env(db, env)


def test_day12_driver_unauthorized_vehicle_rejected(db: Session):
    """Tài xế lạ (không quản lý xe của tuyến) không được phép start hoặc end ca chạy."""
    env = _seed_driver_env(db)
    try:
        route = env["route"]
        other_driver = env["driver_2"]

        # Thử bắt đầu tuyến
        with pytest.raises(HTTPException) as exc_info:
            start_route(route_id=route.id, db=db, current_driver=other_driver)

        assert exc_info.value.status_code == 403
        assert "không thuộc xe do bạn quản lý" in exc_info.value.detail

        # Thử kết thúc tuyến
        with pytest.raises(HTTPException) as exc_info2:
            end_route(route_id=route.id, db=db, current_driver=other_driver)

        assert exc_info2.value.status_code == 403
        assert "không thuộc xe do bạn quản lý" in exc_info2.value.detail
    finally:
        _cleanup_env(db, env)


# ══════════════════════════════════════════════════════════════════════════════
# 2. TEST TÀI XẾ QUÉT MÃ QR ĐIỂM DANH HÀNH KHÁCH
# ══════════════════════════════════════════════════════════════════════════════

def test_day12_driver_verify_ticket_qr_success(db: Session):
    """Tài xế quét mã QR hợp lệ: vé chuyển sang USED và trả về tên học sinh."""
    env = _seed_driver_env(db)
    try:
        ticket = env["ticket"]
        driver = env["driver_1"]

        req = QRVerifyRequest(qr_code=ticket.qr_code)
        res = verify_ticket_qr(request=req, db=db, current_driver=driver)

        assert res.id == ticket.id
        assert res.status == TicketStatus.USED
        assert res.student_name == "Học sinh C"

        db.refresh(ticket)
        assert ticket.status == TicketStatus.USED
    finally:
        _cleanup_env(db, env)


def test_day12_driver_verify_already_used_ticket_rejected(db: Session):
    """Vé đã sử dụng rồi (USED) không được phép điểm danh lần thứ 2."""
    env = _seed_driver_env(db)
    try:
        ticket = env["ticket"]
        driver = env["driver_1"]

        # Điểm danh lần 1
        req = QRVerifyRequest(qr_code=ticket.qr_code)
        verify_ticket_qr(request=req, db=db, current_driver=driver)

        # Điểm danh lần 2: Phải từ chối 400
        with pytest.raises(HTTPException) as exc_info:
            verify_ticket_qr(request=req, db=db, current_driver=driver)

        assert exc_info.value.status_code == 400
        assert "đã được điểm danh trước đó" in exc_info.value.detail
    finally:
        _cleanup_env(db, env)
