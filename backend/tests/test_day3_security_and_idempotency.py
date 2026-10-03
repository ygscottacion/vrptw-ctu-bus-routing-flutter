"""
test_day3_security_and_idempotency.py — Comprehensive Unit & Integration Tests for Day 3 Fixes

Covers:
- Group A: Route State Machine transitions (pending->start->end = 200, completed->start = 409, pending->end = 409)
- Group B: Route Ownership Guard (D2 start/end on D1's route = 403, state unchanged)
- Group C: Idempotency & Ticket Purchase (Same key 2x = 201 + cached response, balance -7,000 once; same key diff body = 409 Conflict)
"""
import uuid
import datetime
import pytest
from fastapi import HTTPException, status
from sqlalchemy import text
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStatus
from app.models.wallet import Wallet
from app.schemas.ticket import TicketReserveRequest
from app.services.wallet_service import purchase_ticket
from app.core.idempotency import process_idempotency_key


def _seed_day3_test_entities(db):
    """Seed test profiles, vehicles, depot, location, routes, and wallet."""
    student_id = uuid.uuid4()
    driver1_id = uuid.uuid4()
    driver2_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    vehicle1_id = uuid.uuid4()
    vehicle2_id = uuid.uuid4()
    loc_id = uuid.uuid4()

    student = Profile(id=student_id, role=ProfileRole.PASSENGER, full_name="Student Test")
    driver1 = Profile(id=driver1_id, role=ProfileRole.DRIVER, full_name="Driver 1")
    driver2 = Profile(id=driver2_id, role=ProfileRole.DRIVER, full_name="Driver 2")
    admin = Profile(id=admin_id, role=ProfileRole.ADMIN, full_name="Admin Test")

    vehicle1 = Vehicle(id=vehicle1_id, license_plate="65A-11111", capacity=30, driver_id=driver1_id)
    vehicle2 = Vehicle(id=vehicle2_id, license_plate="65A-22222", capacity=30, driver_id=driver2_id)

    location = Location(id=loc_id, code="LOC_TEST", name="Trạm KTX B", latitude=10.03, longitude=105.77)
    wallet = Wallet(user_id=student_id, balance=200000)

    db.add_all([student, driver1, driver2, admin, vehicle1, vehicle2, location, wallet])
    db.commit()

    return {
        "student": student,
        "driver1": driver1,
        "driver2": driver2,
        "admin": admin,
        "vehicle1": vehicle1,
        "vehicle2": vehicle2,
        "location": location,
        "wallet": wallet,
    }


# ── Group A: State Machine Validation ─────────────────────────────────────────
def test_group_a_route_state_machine_transitions(db_session):
    """
    Xác minh State Machine của Route:
    - pending -> in_progress (start) -> completed (end): PASS (200)
    - completed -> start: FAIL (409 Conflict)
    - pending -> end: FAIL (409 Conflict)
    """
    db = db_session
    entities = _seed_day3_test_entities(db)
    driver1 = entities["driver1"]
    vehicle1 = entities["vehicle1"]

    route_pending = Route(
        id=uuid.uuid4(),
        service_date=datetime.date(2026, 10, 15),
        session_id="MORNING_1",
        trip_type="pickup",
        vehicle_id=vehicle1.id,
        status=RouteStatus.PENDING,
    )
    route_completed = Route(
        id=uuid.uuid4(),
        service_date=datetime.date(2026, 10, 15),
        session_id="MORNING_2",
        trip_type="pickup",
        vehicle_id=vehicle1.id,
        status=RouteStatus.COMPLETED,
    )
    db.add_all([route_pending, route_completed])
    db.commit()

    from app.api.v1.endpoints.routes import start_route, end_route

    # 1. start route pending -> in_progress
    res1 = start_route(route_id=route_pending.id, db=db, current_driver=driver1)
    assert res1.status == RouteStatus.IN_PROGRESS

    # 2. end route in_progress -> completed
    res2 = end_route(route_id=route_pending.id, db=db, current_driver=driver1)
    assert res2.status == RouteStatus.COMPLETED

    # 3. start route completed -> 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        start_route(route_id=route_completed.id, db=db, current_driver=driver1)
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "Không thể chuyển tuyến từ trạng thái 'completed' sang 'in_progress'" in exc_info.value.detail

    # 4. end route pending (create new pending route) -> 409 Conflict
    route_pending2 = Route(
        id=uuid.uuid4(),
        service_date=datetime.date(2026, 10, 16),
        session_id="MORNING_1",
        trip_type="pickup",
        vehicle_id=vehicle1.id,
        status=RouteStatus.PENDING,
    )
    db.add(route_pending2)
    db.commit()

    with pytest.raises(HTTPException) as exc_info2:
        end_route(route_id=route_pending2.id, db=db, current_driver=driver1)
    assert exc_info2.value.status_code == status.HTTP_409_CONFLICT
    assert "Không thể chuyển tuyến từ trạng thái 'pending' sang 'completed'" in exc_info2.value.detail


# ── Group B: Ownership Checks & Error Order ──────────────────────────────────
def test_group_b_driver_ownership_guard(db_session):
    """
    Xác minh Driver 2 không thể start/end route của Driver 1:
    - Trả về 403 Forbidden
    - Trạng thái route của Driver 1 giữ nguyên pending
    """
    db = db_session
    entities = _seed_day3_test_entities(db)
    driver1 = entities["driver1"]
    driver2 = entities["driver2"]
    vehicle1 = entities["vehicle1"]

    route_d1 = Route(
        id=uuid.uuid4(),
        service_date=datetime.date(2026, 10, 15),
        session_id="MORNING_1",
        trip_type="pickup",
        vehicle_id=vehicle1.id,
        status=RouteStatus.PENDING,
    )
    db.add(route_d1)
    db.commit()

    from app.api.v1.endpoints.routes import start_route, end_route

    # Driver 2 tries to start Driver 1's route -> 403
    with pytest.raises(HTTPException) as exc1:
        start_route(route_id=route_d1.id, db=db, current_driver=driver2)
    assert exc1.value.status_code == status.HTTP_403_FORBIDDEN

    # Verify route status remains pending
    db.refresh(route_d1)
    assert route_d1.status == RouteStatus.PENDING

    # Driver 2 tries to end Driver 1's route -> 403
    with pytest.raises(HTTPException) as exc2:
        end_route(route_id=route_d1.id, db=db, current_driver=driver2)
    assert exc2.value.status_code == status.HTTP_403_FORBIDDEN

    db.refresh(route_d1)
    assert route_d1.status == RouteStatus.PENDING


# ── Group C: Atomic Idempotent Ticket Purchase ───────────────────────────────
def test_group_c_atomic_idempotency_ticket_purchase(db_session):
    """
    Xác minh Idempotency Key khi đặt vé:
    - Mua vé 2 lần với cùng Key: Lần 1 mua thành công (201), ví -7000. Lần 2 trả cached response (201), ví giữ nguyên.
    - Mua vé với cùng Key nhưng payload khác: Trả 409 Conflict.
    """
    db = db_session
    entities = _seed_day3_test_entities(db)
    student = entities["student"]
    location = entities["location"]
    wallet = entities["wallet"]

    req_payload1 = TicketReserveRequest(
        service_date=datetime.date(2026, 10, 20),
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=location.id,
    )

    idem_key = "KEY-TEST-UNIT-999"

    # Lần 1: process_idempotency_key -> None -> purchase_ticket -> 201 Created
    existing, req_hash = process_idempotency_key(
        db=db, user_id=student.id, endpoint="/api/v1/tickets/reserve", key=idem_key, request_data=req_payload1.model_dump()
    )
    assert existing is None

    ticket1 = purchase_ticket(
        db=db,
        user_id=student.id,
        ticket_in=req_payload1,
        idempotency_key=idem_key,
        request_hash=req_hash,
        endpoint="/api/v1/tickets/reserve",
    )
    assert ticket1.status == TicketStatus.PAID_PENDING_ROUTE
    db.refresh(wallet)
    assert wallet.balance == 193000

    # Lần 2: process_idempotency_key -> trả về existing cached record
    existing2, req_hash2 = process_idempotency_key(
        db=db, user_id=student.id, endpoint="/api/v1/tickets/reserve", key=idem_key, request_data=req_payload1.model_dump()
    )
    assert existing2 is not None
    assert existing2.response_code == 201
    assert existing2.response_body["id"] == str(ticket1.id)

    # Balance check: wallet balance must still be 193,000 (deducted ONCE)
    db.refresh(wallet)
    assert wallet.balance == 193000

    # Lần 3: process_idempotency_key với payload khác -> 409 Conflict
    req_payload_diff = TicketReserveRequest(
        service_date=datetime.date(2026, 10, 20),
        session_id="MORNING_2",  # Different session
        trip_type="pickup",
        pickup_location_id=location.id,
    )
    with pytest.raises(HTTPException) as exc_diff:
        process_idempotency_key(
            db=db, user_id=student.id, endpoint="/api/v1/tickets/reserve", key=idem_key, request_data=req_payload_diff.model_dump()
        )
    assert exc_diff.value.status_code == status.HTTP_409_CONFLICT
