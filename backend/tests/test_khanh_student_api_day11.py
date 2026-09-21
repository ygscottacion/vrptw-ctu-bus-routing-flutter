"""
test_khanh_student_api_day11.py
================================
Bộ kiểm thử tự động cho nhiệm vụ của Khánh:
Ngày 11 — API Sinh Viên:
1. Đặt vé (reserve) trước hạn chót 22:00 D-1 thành công, sinh QR và status RESERVED.
2. Chặn đặt vé sau hạn chót 22:00 D-1 (400 Bad Request).
3. Chặn đặt trùng vé trong cùng ca/chiều (400 Bad Request).
4. Endpoint GET /api/v1/tickets/me trả về đầy đủ trạm đón và ETA thực tế sau khi phân tuyến.
5. Hủy vé trước hạn chót (chỉ cho phép khi RESERVED).
"""

import uuid
import datetime
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.timezone import VN_TZ
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.schemas.ticket import TicketReserveRequest
from app.api.v1.endpoints.tickets import reserve_ticket, read_my_tickets, cancel_ticket


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

        # Profiles & auth.users
        for uid in env.get("user_ids", []):
            db.execute(sa_text("DELETE FROM profiles WHERE id = :id"), {"id": str(uid)})
            db.execute(sa_text("DELETE FROM auth.users WHERE id = :id"), {"id": str(uid)})

        # Vehicles & Locations
        for vid in env.get("vehicle_ids", []):
            db.execute(sa_text("DELETE FROM vehicles WHERE id = :id"), {"id": str(vid)})
        for lid in env.get("location_ids", []):
            db.execute(sa_text("DELETE FROM locations WHERE id = :id"), {"id": str(lid)})

        db.commit()
    except Exception as exc:
        db.rollback()
        import logging
        logging.getLogger(__name__).warning(f"[cleanup_day11] Warning: {exc}")


def _seed_student_env(db: Session) -> dict:
    """Tạo học sinh, trạm đón và xe cho test Day 11."""
    st = Location(
        id=uuid.uuid4(),
        code=f"ST_{uuid.uuid4().hex[:6]}",
        name="Trạm KTX Khu B",
        latitude=10.0350,
        longitude=105.7700,
    )
    db.add(st)

    student_id = uuid.uuid4()
    db.flush()
    _ensure_auth_user(db, student_id)
    db.commit()

    student = db.query(Profile).filter(Profile.id == student_id).first()
    if not student:
        student = Profile(
            id=student_id,
            role=ProfileRole.PASSENGER,
            full_name="Sinh viên Kiểm thử Day 11",
        )
        db.add(student)
    else:
        student.role = ProfileRole.PASSENGER
        student.full_name = "Sinh viên Kiểm thử Day 11"
    db.commit()

    service_date = datetime.date(2026, 10, 15)
    session_id = "MORNING_1"
    trip_type = "pickup"

    return {
        "student": student,
        "station": st,
        "service_date": service_date,
        "session_id": session_id,
        "trip_type": trip_type,
        "user_ids": [student_id],
        "location_ids": [st.id],
        "ticket_ids": [],
        "vehicle_ids": [],
        "route_ids": [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 1. TEST ĐẶT VÉ TRƯỚC HẠN CHÓT (SUCCESS) VÀ CHẶN ĐẶT TRÙNG
# ══════════════════════════════════════════════════════════════════════════════

def test_day11_student_reserve_ticket_before_deadline_success(db: Session):
    """Đặt vé trước hạn chót 22:00 D-1 thành công, sinh mã QR và trạng thái RESERVED."""
    env = _seed_student_env(db)
    try:
        valid_booking_time = datetime.datetime.combine(
            env["service_date"] - datetime.timedelta(days=1),
            datetime.time(hour=15, minute=0, second=0),
            tzinfo=VN_TZ,
        )
        with patch("app.api.v1.endpoints.tickets.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = valid_booking_time
            mock_dt.datetime.combine = datetime.datetime.combine
            mock_dt.timedelta = datetime.timedelta
            mock_dt.time = datetime.time

            req = TicketReserveRequest(
                service_date=env["service_date"],
                session_id=env["session_id"],
                trip_type=env["trip_type"],
                pickup_location_id=env["station"].id,
            )

            ticket = reserve_ticket(
                ticket_in=req,
                x_idempotency_key=str(uuid.uuid4()),
                db=db,
                current_profile=env["student"],
            )

            assert ticket.status == TicketStatus.RESERVED
            assert ticket.qr_code.startswith("TICKET_")
            assert ticket.user_id == env["student"].id
            assert ticket.route_id is None
            env["ticket_ids"].append(ticket.id)
    finally:
        _cleanup_env(db, env)


def test_day11_student_reserve_ticket_after_deadline_rejected(db: Session):
    """Đặt vé sau hạn chót 22:00 D-1 phải bị từ chối 400 Bad Request."""
    env = _seed_student_env(db)
    try:
        late_booking_time = datetime.datetime.combine(
            env["service_date"] - datetime.timedelta(days=1),
            datetime.time(hour=22, minute=5, second=0),
            tzinfo=VN_TZ,
        )
        with patch("app.api.v1.endpoints.tickets.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = late_booking_time
            mock_dt.datetime.combine = datetime.datetime.combine
            mock_dt.timedelta = datetime.timedelta
            mock_dt.time = datetime.time

            req = TicketReserveRequest(
                service_date=env["service_date"],
                session_id=env["session_id"],
                trip_type=env["trip_type"],
                pickup_location_id=env["station"].id,
            )

            with pytest.raises(HTTPException) as exc_info:
                reserve_ticket(
                    ticket_in=req,
                    x_idempotency_key=None,
                    db=db,
                    current_profile=env["student"],
                )

            assert exc_info.value.status_code == 400
            assert "quá hạn đặt vé" in exc_info.value.detail
    finally:
        _cleanup_env(db, env)


def test_day11_student_reserve_ticket_duplicate_rejected(db: Session):
    """Sinh viên không được phép đặt 2 vé cho cùng ca/ngày/chiều (chống trùng lặp)."""
    env = _seed_student_env(db)
    try:
        valid_booking_time = datetime.datetime.combine(
            env["service_date"] - datetime.timedelta(days=1),
            datetime.time(hour=14, minute=0, second=0),
            tzinfo=VN_TZ,
        )
        with patch("app.api.v1.endpoints.tickets.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = valid_booking_time
            mock_dt.datetime.combine = datetime.datetime.combine
            mock_dt.timedelta = datetime.timedelta
            mock_dt.time = datetime.time

            req = TicketReserveRequest(
                service_date=env["service_date"],
                session_id=env["session_id"],
                trip_type=env["trip_type"],
                pickup_location_id=env["station"].id,
            )

            # Lần 1: Thành công
            t1 = reserve_ticket(
                ticket_in=req,
                x_idempotency_key=None,
                db=db,
                current_profile=env["student"],
            )
            env["ticket_ids"].append(t1.id)

            # Lần 2: Phải bị từ chối 400
            with pytest.raises(HTTPException) as exc_info:
                reserve_ticket(
                    ticket_in=req,
                    x_idempotency_key=None,
                    db=db,
                    current_profile=env["student"],
                )

            assert exc_info.value.status_code == 400
            assert "Bạn đã giữ chỗ cho chuyến đi này rồi" in exc_info.value.detail
    finally:
        _cleanup_env(db, env)


# ══════════════════════════════════════════════════════════════════════════════
# 2. TEST GET /tickets/me TRẢ VỀ ĐẦY ĐỦ TRẠM ĐÓN VÀ ETA THỰC TẾ
# ══════════════════════════════════════════════════════════════════════════════

def test_day11_student_read_my_tickets_includes_station_and_eta(db: Session):
    """GET /api/v1/tickets/me trả về thông tin trạm đón và ETA thực tế sau khi phân tuyến."""
    env = _seed_student_env(db)
    try:
        # Tạo Route và RouteStop có arrival_time
        route = Route(
            id=uuid.uuid4(),
            service_date=env["service_date"],
            session_id=env["session_id"],
            trip_type=env["trip_type"],
            status=RouteStatus.PENDING,
            total_distance=12.5,
        )
        db.add(route)
        db.flush()
        env["route_ids"].append(route.id)

        eta_time = datetime.datetime(2026, 10, 15, 6, 25, 0, tzinfo=datetime.timezone.utc)
        stop = RouteStop(
            id=uuid.uuid4(),
            route_id=route.id,
            location_id=env["station"].id,
            stop_order=1,
            arrival_time=eta_time,
        )
        db.add(stop)

        # Tạo vé ở trạng thái ASSIGNED được gán vào route
        ticket = Ticket(
            id=uuid.uuid4(),
            user_id=env["student"].id,
            route_id=route.id,
            service_date=env["service_date"],
            session_id=env["session_id"],
            trip_type=env["trip_type"],
            pickup_location_id=env["station"].id,
            qr_code=f"QR_{uuid.uuid4().hex[:8]}",
            status=TicketStatus.ASSIGNED,
        )
        db.add(ticket)
        db.commit()
        env["ticket_ids"].append(ticket.id)

        # Gọi endpoint read_my_tickets
        tickets_res = read_my_tickets(db=db, current_profile=env["student"])

        assert len(tickets_res) >= 1
        matched = [t for t in tickets_res if t.id == ticket.id][0]

        # Kiểm tra trạm đón và ETA
        assert matched.pickup_location is not None
        assert matched.pickup_location.name == "Trạm KTX Khu B"
        assert matched.pickup_eta == eta_time
    finally:
        _cleanup_env(db, env)


# ══════════════════════════════════════════════════════════════════════════════
# 3. TEST HỦY VÉ TRƯỚC HẠN CHÓT
# ══════════════════════════════════════════════════════════════════════════════

def test_day11_student_cancel_ticket_before_deadline(db: Session):
    """Sinh viên được phép hủy vé khi còn ở trạng thái RESERVED trước hạn chót."""
    env = _seed_student_env(db)
    try:
        ticket = Ticket(
            id=uuid.uuid4(),
            user_id=env["student"].id,
            service_date=env["service_date"],
            session_id=env["session_id"],
            trip_type=env["trip_type"],
            pickup_location_id=env["station"].id,
            qr_code=f"QR_{uuid.uuid4().hex[:8]}",
            status=TicketStatus.RESERVED,
        )
        db.add(ticket)
        db.commit()
        env["ticket_ids"].append(ticket.id)

        valid_time = datetime.datetime.combine(
            env["service_date"] - datetime.timedelta(days=1),
            datetime.time(hour=18, minute=0, second=0),
            tzinfo=VN_TZ,
        )
        with patch("app.api.v1.endpoints.tickets.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = valid_time
            mock_dt.datetime.combine = datetime.datetime.combine
            mock_dt.timedelta = datetime.timedelta
            mock_dt.time = datetime.time

            cancelled = cancel_ticket(
                ticket_id=ticket.id,
                x_idempotency_key=None,
                db=db,
                current_profile=env["student"],
            )

            assert cancelled.status == TicketStatus.CANCELLED
            db.refresh(ticket)
            assert ticket.status == TicketStatus.CANCELLED
    finally:
        _cleanup_env(db, env)
