import uuid
import datetime
import pytest
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.services.route_worker import (
    run_route_job_worker,
    _build_uuid_lookup,
    _lookup_solver_node,
    _validate_route_and_stops,
    UnmappedSolverNodeError,
    RouteStopValidationError,
)
from app.services.vrptw_solver import VRPTWSolverService
from app.schemas.route import RouteResponse


# ── 1. Unit Test Mapping (node_key → UUID) ───────────────────────────────────

def test_unit_uuid_mapping():
    depot_id = uuid.uuid4()
    loc0_id = uuid.uuid4()
    loc1_id = uuid.uuid4()

    depot_loc = Location(id=str(depot_id), name="Depot CTU", latitude=10.03, longitude=105.77)
    loc0 = Location(id=str(loc0_id), name="Trạm 1", latitude=10.04, longitude=105.78)
    loc1 = Location(id=str(loc1_id), name="Trạm 2", latitude=10.05, longitude=105.79)

    locations = [loc0, loc1]
    location_dicts = [
        {"id": "location_0", "name": "Trạm 1"},
        {"id": "location_1", "name": "Trạm 2"},
    ]

    lookup = _build_uuid_lookup(depot_id, locations, location_dicts)

    # Assert valid node keys map to correct UUIDs
    assert lookup["depot"] == depot_id
    assert lookup["SCHOOL"] == depot_id
    assert lookup["location_0"] == loc0_id
    assert lookup["location_1"] == loc1_id
    assert lookup["0"] == loc0_id
    assert lookup["1"] == loc1_id
    with pytest.raises(UnmappedSolverNodeError):
        _lookup_solver_node(lookup, "not-a-node", "job-test")
    with pytest.raises(TypeError):
        lookup["location_2"] = uuid.uuid4()

# ── 2. Unit Test Transaction Rollback ──────────────────────────────────────────

def test_unit_transaction_rollback_on_error(db_session):
    """
    Cố tình gây lỗi tại stop thứ 3, assert rằng sau đó KHÔNG còn Route, RouteStop nào
    được lưu trong DB và tất cả Ticket vẫn giữ nguyên trạng thái RESERVED.
    """
    depot_id = uuid.uuid4()
    loc1_id = uuid.uuid4()
    loc2_id = uuid.uuid4()

    depot = Location(id=depot_id, name="Depot Rollback Test", latitude=10.03, longitude=105.77)
    loc1 = Location(id=loc1_id, name="Trạm R1", latitude=10.04, longitude=105.78)
    loc2 = Location(id=loc2_id, name="Trạm R2", latitude=10.05, longitude=105.79)
    db_session.add_all([depot, loc1, loc2])

    v1 = Vehicle(id=uuid.uuid4(), license_plate="51F-ROLLBACK", capacity=30)
    db_session.add(v1)

    today = datetime.date.today() + datetime.timedelta(days=1)
    user_id = uuid.uuid4()

    t1 = Ticket(
        id=uuid.uuid4(),
        user_id=user_id,
        pickup_location_id=loc1_id,
        service_date=today,
        session_id="MORNING_1",
        trip_type="pickup",
        status=TicketStatus.RESERVED,
        qr_code="QR-ROLLBACK-1",
    )
    t2 = Ticket(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        pickup_location_id=loc2_id,
        service_date=today,
        session_id="MORNING_1",
        trip_type="pickup",
        status=TicketStatus.RESERVED,
        qr_code="QR-ROLLBACK-2",
    )
    db_session.add_all([t1, t2])

    job_id = uuid.uuid4()
    job = RouteJob(
        id=job_id,
        depot_location_id=depot_id,
        service_date=today,
        session_id="MORNING_1",
        trip_type="pickup",
        status=RouteJobStatus.QUEUED,
    )
    db_session.add(job)
    db_session.commit()

    import app.services.route_worker as rw_mod
    original_solver_cls = rw_mod.VRPTWSolverService

    class MockBadNodeSolver:
        def solve(self, depot, locations, vehicles, **kwargs):
            stops = [{"id": "depot", "name": "Depot", "arrival_time": "06:00"}]
            for loc in locations:
                stops.append({"id": loc["id"], "name": loc["name"], "arrival_time": "06:15"})
            stops.append({
                "id": "UNMAPPED_NODE_KEY_ERROR_TEST",
                "name": "Trạm Lỗi Unmapped",
                "arrival_time": "06:45",
            })
            return [{
                "vehicle_id": str(vehicles[0]["id"]) if vehicles else None,
                "total_demand": 2,
                "total_distance_km": 5.0,
                "ordered_stops": stops
            }]

    rw_mod.VRPTWSolverService = MockBadNodeSolver

    try:
        with pytest.raises(UnmappedSolverNodeError):
            run_route_job_worker(db_session, job_id)

        db_session.rollback()

        routes_in_db = db_session.query(Route).filter(Route.route_job_id == job_id).all()
        assert len(routes_in_db) == 0

        stops_in_db = db_session.query(RouteStop).all()
        assert len(stops_in_db) == 0

        t1_refreshed = db_session.query(Ticket).filter(Ticket.id == t1.id).first()
        t2_refreshed = db_session.query(Ticket).filter(Ticket.id == t2.id).first()
        assert t1_refreshed.status == TicketStatus.RESERVED
        assert t2_refreshed.status == TicketStatus.RESERVED

        job_refreshed = db_session.query(RouteJob).filter(RouteJob.id == job_id).first()
        assert job_refreshed.status == RouteJobStatus.FAILED
        assert "UNMAPPED_SOLVER_NODE" in (job_refreshed.error_message or "")
    finally:
        rw_mod.VRPTWSolverService = original_solver_cls


# ── 3. E2E Test Kịch bản Gốc của Bug & Regression Test ───────────────────────

def test_e2e_bug_vrptw_01_scenario(db_session):
    """
    E2E Test theo đúng kịch bản gốc làm nổ BUG-VRPTW-01:
    - 1 Depot, 5 Trạm đón sinh viên, 2 Xe buýt, 5 Sinh viên đăng ký 5 vé.
    """
    depot_id = uuid.uuid4()
    depot = Location(id=depot_id, name="Depot Đại học Cần Thơ", latitude=10.0302, longitude=105.7721)
    db_session.add(depot)

    locations = []
    for i in range(1, 6):
        loc_id = uuid.uuid4()
        loc = Location(
            id=loc_id,
            name=f"Trạm Sinh Viên {i}",
            latitude=10.0302 + i * 0.005,
            longitude=105.7721 + i * 0.005,
        )
        locations.append(loc)
        db_session.add(loc)

    v1 = Vehicle(id=uuid.uuid4(), license_plate="51F-000.01", capacity=30)
    v2 = Vehicle(id=uuid.uuid4(), license_plate="51F-000.02", capacity=30)
    db_session.add_all([v1, v2])

    today = datetime.date.today() + datetime.timedelta(days=1)
    tickets = []
    for i, loc in enumerate(locations):
        t = Ticket(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            pickup_location_id=loc.id,
            service_date=today,
            session_id="MORNING_1",
            trip_type="pickup",
            status=TicketStatus.RESERVED,
            qr_code=f"QR-BUG-01-{i+1}",
        )
        tickets.append(t)
        db_session.add(t)

    job_id = uuid.uuid4()
    job = RouteJob(
        id=job_id,
        depot_location_id=depot_id,
        service_date=today,
        session_id="MORNING_1",
        trip_type="pickup",
        status=RouteJobStatus.QUEUED,
    )
    db_session.add(job)
    db_session.commit()

    import app.services.route_worker as rw_mod
    original_solver_cls = rw_mod.VRPTWSolverService
    rw_mod.VRPTWSolverService = lambda: VRPTWSolverService(use_static_matrix=True)

    try:
        updated_job = run_route_job_worker(db_session, job_id)

        assert updated_job.status == RouteJobStatus.SUCCEEDED
        assert updated_job.error_message is None

        assigned_tickets = db_session.query(Ticket).filter(Ticket.status == TicketStatus.ASSIGNED).all()
        assert len(assigned_tickets) == 5

        routes = db_session.query(Route).filter(Route.route_job_id == job_id).all()
        assert len(routes) >= 1

        total_assigned = db_session.query(Ticket).filter(Ticket.status == TicketStatus.ASSIGNED).count()
        assert total_assigned == 5

        # Assert 4: RouteStops có ĐỦ depot + pickup stops — FIX DỨT ĐIỂM BUG-VRPTW-01
        assert len(routes) == 1
        assert len(tickets) == 5
        for r in routes:
            stops = db_session.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.stop_order).all()
            assert len(stops) == 6
            assert str(stops[0].location_id) == str(depot_id)
            assert stops[0].stop_order == 1
            assert r.passenger_count == 5
            for idx, s in enumerate(stops):
                assert s.stop_order == idx + 1

            # The same schema used by driver/student mobile clients contains all stops.
            payload = RouteResponse.model_validate(r)
            assert payload.passenger_count == 5
            assert len(payload.stops) == 6

    finally:
        rw_mod.VRPTWSolverService = original_solver_cls


def test_regression_location_0_bug(db_session):
    """
    Regression Test riêng cho chính lỗi node key 'location_0'.
    """
    depot_id = uuid.uuid4()
    loc0_id = uuid.uuid4()

    depot = Location(id=depot_id, name="Depot Regression", latitude=10.03, longitude=105.77)
    loc0 = Location(id=loc0_id, name="Trạm location_0", latitude=10.04, longitude=105.78)
    db_session.add_all([depot, loc0])

    v1 = Vehicle(id=uuid.uuid4(), license_plate="51F-REGRESSION", capacity=30)
    db_session.add(v1)

    today = datetime.date.today() + datetime.timedelta(days=2)
    user_id = uuid.uuid4()

    t = Ticket(
        id=uuid.uuid4(),
        user_id=user_id,
        pickup_location_id=loc0_id,
        service_date=today,
        session_id="MORNING_1",
        trip_type="pickup",
        status=TicketStatus.RESERVED,
        qr_code="QR-REG-0",
    )
    db_session.add(t)

    job_id = uuid.uuid4()
    job = RouteJob(
        id=job_id,
        depot_location_id=depot_id,
        service_date=today,
        session_id="MORNING_1",
        trip_type="pickup",
        status=RouteJobStatus.QUEUED,
    )
    db_session.add(job)
    db_session.commit()

    import app.services.route_worker as rw_mod
    original_solver_cls = rw_mod.VRPTWSolverService
    v1_id = str(v1.id)
    depot_id_str = str(depot_id)
    loc0_id_str = str(loc0_id)

    class MockLocation0Solver:
        def solve(self, *args, **kwargs):
            return [{
                "vehicle_id": v1_id,
                "total_demand": 1,
                "total_distance_km": 5.2,
                "ordered_stops": [
                    {"id": "depot", "name": "Depot", "arrival_time": "06:00"},
                    {"id": "location_0", "name": "Trạm location_0", "arrival_time": "06:15"},
                ]
            }]

    rw_mod.VRPTWSolverService = MockLocation0Solver

    try:
        updated_job = run_route_job_worker(db_session, job_id)
        assert updated_job.status == RouteJobStatus.SUCCEEDED, f"Job failed: {updated_job.error_message}"

        stops = db_session.query(RouteStop).order_by(RouteStop.stop_order).all()
        assert len(stops) == 2
        assert str(stops[0].location_id) == depot_id_str
        assert str(stops[1].location_id) == loc0_id_str  # Map đúng location_0 -> loc0_id (UUID)
    finally:
        rw_mod.VRPTWSolverService = original_solver_cls


def test_generate_api_persists_complete_stop_manifest(db_session, monkeypatch):
    """Integration: POST /routes/generate returns a complete mobile manifest."""
    from app.api import deps
    from app.core.config import settings
    from app.main import app
    import app.services.route_worker as rw_mod

    depot_id, pickup_id = uuid.uuid4(), uuid.uuid4()
    db_session.add_all([
        Location(id=depot_id, name="API depot", latitude=10.03, longitude=105.77),
        Location(id=pickup_id, name="API pickup", latitude=10.04, longitude=105.78),
        Vehicle(id=uuid.uuid4(), license_plate="51F-API", capacity=30),
        Ticket(id=uuid.uuid4(), user_id=uuid.uuid4(), pickup_location_id=pickup_id,
               service_date=datetime.date.today(), session_id="MORNING_1", trip_type="pickup",
               status=TicketStatus.RESERVED, qr_code="QR-API-STOP-MANIFEST"),
    ])
    db_session.commit()
    monkeypatch.setattr(rw_mod, "VRPTWSolverService", lambda: VRPTWSolverService(use_static_matrix=True))
    previous_secret = settings.CRON_SECRET
    settings.CRON_SECRET = "test-cron-secret"
    app.dependency_overrides[deps.get_db] = lambda: db_session
    try:
        response = TestClient(app).post(
            "/api/v1/routes/generate",
            headers={"X-Cron-Secret": "test-cron-secret"},
            json={"service_date": str(datetime.date.today()), "session_id": "MORNING_1", "trip_type": "pickup", "depot_location_id": str(depot_id)},
        )
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "succeeded"
        route = db_session.query(Route).one()
        assert db_session.query(RouteStop).filter(RouteStop.route_id == route.id).count() == 2
        assert RouteResponse.model_validate(route).passenger_count == 1
    finally:
        app.dependency_overrides.clear()
        settings.CRON_SECRET = previous_secret
