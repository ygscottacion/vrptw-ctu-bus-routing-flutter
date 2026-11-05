import datetime
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api.v1.endpoints.gps import create_gps_location, read_latest_gps_location
from app.models.location import Location
from app.models.profile import Profile, ProfileRole
from app.models.route import Route, RouteStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.vehicle import Vehicle
from app.schemas.gps import GpsLocationCreate


def _profile(db_session, role):
    profile_id = uuid.uuid4()
    db_session.execute(
        text("INSERT INTO auth.users (id) VALUES (:id)"),
        {"id": str(profile_id)},
    )
    profile = Profile(id=profile_id, role=role, full_name=role.value)
    db_session.add(profile)
    db_session.flush()
    return profile


def _active_route(db_session, driver):
    vehicle = Vehicle(
        id=uuid.uuid4(), license_plate=f"GPS-{uuid.uuid4().hex[:8]}", driver_id=driver.id
    )
    db_session.add(vehicle)
    location = Location(
        id=uuid.uuid4(),
        code=f"GPS-{uuid.uuid4().hex[:8]}",
        name="GPS test stop",
        latitude=10.03,
        longitude=105.77,
        demand=1,
    )
    db_session.add(location)
    route = Route(
        id=uuid.uuid4(),
        service_date=datetime.date.today(),
        session_id="MORNING_1",
        trip_type="pickup",
        vehicle_id=vehicle.id,
        status=RouteStatus.IN_PROGRESS,
    )
    db_session.add(route)
    db_session.flush()
    return route, location


def test_driver_can_post_gps_and_assigned_student_can_read_latest(db_session):
    driver = _profile(db_session, ProfileRole.DRIVER)
    student = _profile(db_session, ProfileRole.PASSENGER)
    route, location = _active_route(db_session, driver)
    db_session.add(
        Ticket(
            id=uuid.uuid4(),
            user_id=student.id,
            route_id=route.id,
            service_date=route.service_date,
            session_id=route.session_id,
            trip_type=route.trip_type,
            pickup_location_id=location.id,
            qr_code=f"GPS-{uuid.uuid4().hex}",
            status=TicketStatus.ASSIGNED,
        )
    )
    db_session.commit()

    request = GpsLocationCreate(
        route_id=route.id,
        latitude=10.031,
        longitude=105.771,
        heading=45,
        speed=18,
        accuracy=7,
    )
    created = create_gps_location(request, db_session, driver)
    latest = read_latest_gps_location(route.id, db_session, student)

    assert created.latitude == pytest.approx(10.031)
    assert latest.route_id == route.id
    assert latest.longitude == pytest.approx(105.771)
    assert latest.recorded_at is not None

    db_session.query(Ticket).filter(Ticket.route_id == route.id).update(
        {Ticket.status: TicketStatus.USED}
    )
    db_session.commit()
    assert read_latest_gps_location(route.id, db_session, student).id == created.id


def test_student_without_assigned_ticket_cannot_read_gps(db_session):
    driver = _profile(db_session, ProfileRole.DRIVER)
    stranger = _profile(db_session, ProfileRole.PASSENGER)
    route, _ = _active_route(db_session, driver)
    db_session.commit()

    with pytest.raises(HTTPException) as error:
        read_latest_gps_location(route.id, db_session, stranger)

    assert error.value.status_code == 404


def test_driver_cannot_post_gps_for_another_drivers_route(db_session):
    assigned_driver = _profile(db_session, ProfileRole.DRIVER)
    other_driver = _profile(db_session, ProfileRole.DRIVER)
    route, _ = _active_route(db_session, assigned_driver)
    db_session.commit()

    with pytest.raises(HTTPException) as error:
        create_gps_location(
            GpsLocationCreate(
                route_id=route.id,
                latitude=10.03,
                longitude=105.77,
            ),
            db_session,
            other_driver,
        )

    assert error.value.status_code == 404
