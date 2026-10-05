import datetime
import uuid

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.tickets import verify_ticket_qr
from app.models.location import Location
from app.models.profile import Profile, ProfileRole
from app.models.route import Route, RouteStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.vehicle import Vehicle
from app.schemas.ticket import QRVerifyRequest
from app.core.database import Base


def _seed_qr_case(db, *, assign_vehicle=True):
    driver_id, other_driver_id, student_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    users = Base.metadata.tables["auth.users"]
    db.execute(users.insert(), [{"id": user_id} for user_id in (driver_id, other_driver_id, student_id)])

    driver = Profile(id=driver_id, role=ProfileRole.DRIVER, full_name="Driver A")
    other_driver = Profile(id=other_driver_id, role=ProfileRole.DRIVER, full_name="Driver B")
    student = Profile(id=student_id, role=ProfileRole.PASSENGER, full_name="Student A", phone="0900000000")
    db.add_all([driver, other_driver, student])
    db.flush()

    vehicle = Vehicle(id=uuid.uuid4(), license_plate=f"QR-{uuid.uuid4().hex[:8]}", capacity=45, driver_id=driver.id)
    location = Location(
        id=uuid.uuid4(),
        code=f"QR-{uuid.uuid4().hex[:8]}",
        name="QR Test Stop",
        latitude=10.03,
        longitude=105.77,
    )
    db.add_all([vehicle, location])
    db.flush()

    route = Route(
        id=uuid.uuid4(),
        service_date=datetime.date(2026, 10, 6),
        session_id="MORNING_1",
        trip_type="pickup",
        vehicle_id=vehicle.id if assign_vehicle else None,
        status=RouteStatus.PENDING,
        total_distance=1.0,
    )
    db.add(route)
    db.flush()

    ticket = Ticket(
        id=uuid.uuid4(),
        user_id=student.id,
        route_id=route.id,
        service_date=route.service_date,
        session_id=route.session_id,
        trip_type=route.trip_type,
        pickup_location_id=location.id,
        qr_code=f"BUS-{uuid.uuid4().hex[:8].upper()}",
        status=TicketStatus.ASSIGNED,
    )
    db.add(ticket)
    db.commit()
    return {"driver": driver, "other_driver": other_driver, "route": route, "ticket": ticket}


def test_verify_qr_marks_assigned_ticket_used(db_session):
    case = _seed_qr_case(db_session)

    result = verify_ticket_qr(
        request=QRVerifyRequest(qr_code=case["ticket"].qr_code),
        db=db_session,
        current_driver=case["driver"],
    )

    assert result.status == TicketStatus.USED
    assert result.student_name == "Student A"
    assert db_session.get(Ticket, case["ticket"].id).status == TicketStatus.USED


def test_verify_qr_rejects_ticket_from_another_drivers_vehicle(db_session):
    case = _seed_qr_case(db_session)

    with pytest.raises(HTTPException) as exc_info:
        verify_ticket_qr(
            request=QRVerifyRequest(qr_code=case["ticket"].qr_code),
            db=db_session,
            current_driver=case["other_driver"],
        )

    assert exc_info.value.status_code == 403
    assert db_session.get(Ticket, case["ticket"].id).status == TicketStatus.ASSIGNED


def test_verify_qr_rejects_route_without_assigned_vehicle(db_session):
    case = _seed_qr_case(db_session, assign_vehicle=False)

    with pytest.raises(HTTPException) as exc_info:
        verify_ticket_qr(
            request=QRVerifyRequest(qr_code=case["ticket"].qr_code),
            db=db_session,
            current_driver=case["driver"],
        )

    assert exc_info.value.status_code == 403
    assert db_session.get(Ticket, case["ticket"].id).status == TicketStatus.ASSIGNED


def test_verify_qr_rejects_second_scan(db_session):
    case = _seed_qr_case(db_session)
    request = QRVerifyRequest(qr_code=case["ticket"].qr_code)

    verify_ticket_qr(request=request, db=db_session, current_driver=case["driver"])
    with pytest.raises(HTTPException) as exc_info:
        verify_ticket_qr(request=request, db=db_session, current_driver=case["driver"])

    assert exc_info.value.status_code == 400
    assert "đã được điểm danh trước đó" in exc_info.value.detail
