import uuid
import datetime
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.api import deps
from app.api.deps import verify_supabase_jwt, get_current_profile, get_current_student
from app.services.route_worker import run_route_job_worker
from app.core.timezone import VN_TZ

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(engine, "connect")
def attach_auth_schema(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("ATTACH DATABASE ':memory:' AS auth;")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def test_reserve_and_cancel_ticket():
    db = TestingSessionLocal()
    client = TestClient(app)

    student_id = uuid.uuid4()
    student_profile = Profile(id=student_id, role=ProfileRole.PASSENGER, full_name="Student A")
    db.add(student_profile)

    location = Location(
        id=uuid.uuid4(),
        name="Trạm A - KTX A",
        latitude=10.0302,
        longitude=105.7721,
        demand=1,
    )
    db.add(location)
    db.commit()

    def mock_get_profile():
        return student_profile

    app.dependency_overrides[get_current_profile] = mock_get_profile
    app.dependency_overrides[get_current_student] = mock_get_profile

    future_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=3)).date()

    payload = {
        "service_date": str(future_date),
        "session_id": "MORNING_1",
        "trip_type": "pickup",
        "pickup_location_id": str(location.id),
    }
    headers = {"Authorization": "Bearer mock_token", "X-Idempotency-Key": "key_test_123"}

    # 1. Reserve ticket
    response = client.post("/api/v1/tickets/reserve", json=payload, headers=headers)
    assert response.status_code == 201
    ticket_data = response.json()
    ticket_id = ticket_data["id"]
    assert ticket_data["status"] == "reserved"

    # 2. Cancel ticket
    cancel_resp = client.post(f"/api/v1/tickets/{ticket_id}/cancel", headers={"X-Idempotency-Key": "cancel_key_1"})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    db.close()


def test_route_worker_and_rbac():
    db = TestingSessionLocal()
    client = TestClient(app)

    # 1. Setup Student, Driver, Vehicles & Locations
    student_id = uuid.uuid4()
    driver_id = uuid.uuid4()
    other_student_id = uuid.uuid4()

    student_profile = Profile(id=student_id, role=ProfileRole.PASSENGER, full_name="Student A")
    other_student_profile = Profile(id=other_student_id, role=ProfileRole.PASSENGER, full_name="Student B")
    driver_profile = Profile(id=driver_id, role=ProfileRole.DRIVER, full_name="Driver A")

    db.add_all([student_profile, other_student_profile, driver_profile])

    depot = Location(id=uuid.uuid4(), name="CTU Depot", latitude=10.0302, longitude=105.7721)
    pickup_loc = Location(id=uuid.uuid4(), name="Station 1", latitude=10.032, longitude=105.775)
    db.add_all([depot, pickup_loc])

    vehicle = Vehicle(id=uuid.uuid4(), license_plate="65A-12345", capacity=30, driver_id=driver_id)
    db.add(vehicle)

    run_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()

    ticket_a = Ticket(
        id=uuid.uuid4(),
        user_id=student_id,
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=pickup_loc.id,
        qr_code="QR_TICKET_A",
        status=TicketStatus.RESERVED,
    )
    db.add(ticket_a)

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=depot.id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    # 2. Run Worker Job
    executed_job = run_route_job_worker(db=db, job_id=job.id)
    assert executed_job.status == RouteJobStatus.SUCCEEDED

    # Verify Ticket status changed to ASSIGNED and route_id is populated
    db.refresh(ticket_a)
    assert ticket_a.status == TicketStatus.ASSIGNED
    assert ticket_a.route_id is not None

    generated_route_id = ticket_a.route_id

    # 3. Test Student A RBAC (Can see their assigned route)
    app.dependency_overrides[get_current_profile] = lambda: student_profile
    resp_student_a = client.get("/api/v1/routes")
    assert resp_student_a.status_code == 200
    student_routes = resp_student_a.json()
    assert len(student_routes) == 1
    assert student_routes[0]["id"] == str(generated_route_id)

    # 4. Test Student B RBAC (Cannot see Student A's assigned route)
    app.dependency_overrides[get_current_profile] = lambda: other_student_profile
    resp_student_b = client.get("/api/v1/routes")
    assert resp_student_b.status_code == 200
    assert len(resp_student_b.json()) == 0

    # 5. Test Driver A RBAC (Can see their assigned vehicle route)
    app.dependency_overrides[get_current_profile] = lambda: driver_profile
    resp_driver_a = client.get("/api/v1/routes")
    assert resp_driver_a.status_code == 200
    driver_routes = resp_driver_a.json()
    assert len(driver_routes) == 1
    assert driver_routes[0]["id"] == str(generated_route_id)

    db.close()
