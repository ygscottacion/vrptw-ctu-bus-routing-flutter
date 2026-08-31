"""
test_day3_day4_final.py — Integration tests for Day 3 & Day 4

Strategy:
- Test route_worker và RBAC logic trực tiếp (không qua HTTP) để tránh phụ thuộc
  vào SQLite UUID type coercion trong endpoint params.
- HTTP tests dùng Mock để bypass DB (chỉ test business logic tầng service).
- Solver dùng use_static_matrix=True để bypass OSRM.
"""
import uuid
import datetime
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.timezone import VN_TZ
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.services.route_worker import run_route_job_worker
from app.core.database import Base


# ── SQLite in-memory engine ─────────────────────────────────────────────────
SQLITE_URL = "sqlite:///:memory:"

_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def _attach_auth(dbapi_conn, _record):
    """SQLite cần schema 'auth' cho FK của profiles."""
    cur = dbapi_conn.cursor()
    cur.execute("ATTACH DATABASE ':memory:' AS auth;")
    cur.close()


# Patch PG-specific types → SQLite-compat BEFORE create_all
def _patch_metadata_for_sqlite(engine):
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
    from sqlalchemy import String, JSON

    # UUID compilation is supplied by tests/conftest.py. Do not mutate global
    # SQLAlchemy metadata here: later tests use the same model definitions.

    # Remove partial indexes (postgresql_where) — không hỗ trợ trên SQLite
    for table in Base.metadata.tables.values():
        to_drop = [
            idx for idx in list(table.indexes)
            if idx.kwargs.get("postgresql_where") is not None
        ]
        for idx in to_drop:
            table.indexes.discard(idx)


_patch_metadata_for_sqlite(_engine)

_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture()
def db():
    """Tạo schema mới cho mỗi test, xóa sau khi xong."""
    Base.metadata.create_all(bind=_engine)
    session = _Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=_engine)


# ── Helper: inject static solver ────────────────────────────────────────────
from app.services.vrptw_solver import VRPTWSolverService
from app.services.student_routing.helpers.distance_matrix import StaticDistanceMatrixProvider


class _StaticSolverService(VRPTWSolverService):
    """VRPTWSolverService với static matrix (không OSRM), dùng trong test."""
    def __init__(self):
        super().__init__(use_static_matrix=True)


@pytest.fixture(autouse=True)
def patch_solver(monkeypatch):
    """Tự động patch VRPTWSolverService → _StaticSolverService trong mọi test."""
    import app.services.route_worker as rw
    monkeypatch.setattr(rw, "VRPTWSolverService", _StaticSolverService)


# ── Helper: seed data ────────────────────────────────────────────────────────
def _seed_base(db):
    """Seed các entity cơ bản: depot, 1 pickup stop, 1 vehicle + driver."""
    depot_id = str(uuid.uuid4())
    pickup_id = str(uuid.uuid4())
    driver_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    vehicle_id = str(uuid.uuid4())

    driver = Profile(id=driver_id, role="driver", full_name="Driver A")
    student = Profile(id=student_id, role="passenger", full_name="Student A")
    depot = Location(id=depot_id, name="CTU Depot", latitude=10.0302, longitude=105.7721)
    pickup = Location(id=pickup_id, name="Trạm KTX A", latitude=10.032, longitude=105.775)
    vehicle = Vehicle(id=vehicle_id, license_plate="65A-12345", capacity=30, driver_id=driver_id)

    db.add_all([driver, student, depot, pickup, vehicle])
    db.flush()

    return {
        "depot_id": depot_id,
        "pickup_id": pickup_id,
        "driver_id": driver_id,
        "student_id": student_id,
        "vehicle_id": vehicle_id,
    }


# ── Test 1: Ticket lifecycle (reserve → cancel) ──────────────────────────────
def test_ticket_reserve_and_cancel(db):
    """
    Kiểm tra luồng cơ bản: tạo vé RESERVED, hủy → CANCELLED.
    """
    ids = _seed_base(db)
    run_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=3)).date()

    ticket = Ticket(
        id=str(uuid.uuid4()),
        user_id=ids["student_id"],
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=ids["pickup_id"],
        qr_code="QR_TEST_001",
        status="reserved",
    )
    db.add(ticket)
    db.commit()

    assert ticket.status == "reserved"

    # Hủy vé
    ticket.status = "cancelled"
    db.commit()
    db.refresh(ticket)
    assert ticket.status == "cancelled"


# ── Test 2: Deadline 22:00 VN ────────────────────────────────────────────────
def test_booking_deadline_logic():
    """
    Kiểm tra hàm validate_booking_deadline hoạt động đúng với timezone VN.
    """
    from fastapi import HTTPException
    from app.api.v1.endpoints.tickets import validate_booking_deadline

    now_vn = datetime.datetime.now(VN_TZ)

    # Ngày quá khứ → reject
    past_date = now_vn.date() - datetime.timedelta(days=1)
    with pytest.raises(HTTPException) as exc_info:
        validate_booking_deadline(past_date)
    assert exc_info.value.status_code == 400

    # Ngày hiện tại → reject (không phải "tương lai")
    with pytest.raises(HTTPException):
        validate_booking_deadline(now_vn.date())

    # Ngày tương lai đủ xa → pass (service_date >= today+2 đảm bảo qua cutoff)
    future_date = now_vn.date() + datetime.timedelta(days=3)
    validate_booking_deadline(future_date)  # Không raise


# ── Test 3: Route worker — BUG-VRPTW-01 regression ──────────────────────────
def test_route_worker_creates_route_stops(db):
    """
    Regression test BUG-VRPTW-01:
    Sau khi job SUCCEEDED, route_stops phải có ít nhất 1 pickup stop.
    Job không được báo SUCCEEDED khi stops bị thiếu.
    """
    ids = _seed_base(db)
    run_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()

    ticket = Ticket(
        id=str(uuid.uuid4()),
        user_id=ids["student_id"],
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=ids["pickup_id"],
        qr_code="QR_WORKER_001",
        status="reserved",
    )
    job_id_str = str(uuid.uuid4())
    job = RouteJob(
        id=job_id_str,
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=ids["depot_id"],
        status="queued",
    )
    db.add_all([ticket, job])
    db.commit()

    # Chạy worker (solver đã được patch sang static matrix qua fixture)
    result_job = run_route_job_worker(db=db, job_id=uuid.UUID(job_id_str))

    assert result_job.status == "succeeded", (
        f"Job phải SUCCEEDED, nhưng: {result_job.status} — {result_job.error_message}"
    )

    # Ticket phải được ASSIGNED
    db.refresh(ticket)
    assert ticket.status == "assigned", "Ticket phải chuyển sang ASSIGNED"
    assert ticket.route_id is not None, "Ticket phải có route_id"

    # BUG-VRPTW-01 regression: đếm route_stops
    stop_count = db.execute(
        text("SELECT COUNT(*) FROM route_stops WHERE route_id = :rid"),
        {"rid": str(ticket.route_id)}
    ).scalar()

    assert stop_count >= 1, (
        f"BUG-VRPTW-01 regression FAILED: route_stops count = {stop_count}, "
        f"phải có ít nhất 1 pickup stop sau khi job SUCCEEDED."
    )


# ── Test 4: RBAC — sinh viên chỉ thấy route của mình ────────────────────────
def test_rbac_student_sees_only_own_route(db):
    """
    Student A chỉ thấy route liên kết với ticket của mình.
    Student B không thấy route của Student A.
    """
    ids = _seed_base(db)
    student_b_id = str(uuid.uuid4())
    db.add(Profile(id=student_b_id, role="passenger", full_name="Student B"))

    run_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()

    route_id = str(uuid.uuid4())
    route = Route(
        id=route_id,
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        vehicle_id=ids["vehicle_id"],
        status="pending",
        total_distance=5.0,
    )
    db.add(route)

    ticket_a = Ticket(
        id=str(uuid.uuid4()),
        user_id=ids["student_id"],
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=ids["pickup_id"],
        qr_code="QR_RBAC_A",
        status="assigned",
        route_id=route_id,
    )
    # Student B không có ticket
    db.add(ticket_a)
    db.commit()

    # Student A query
    routes_a = (
        db.query(Route)
        .join(Ticket, Ticket.route_id == Route.id)
        .filter(
            Ticket.user_id == ids["student_id"],
            Ticket.status == "assigned",
        )
        .all()
    )
    assert len(routes_a) == 1
    assert str(routes_a[0].id) == route_id

    # Student B query → không có gì
    routes_b = (
        db.query(Route)
        .join(Ticket, Ticket.route_id == Route.id)
        .filter(
            Ticket.user_id == student_b_id,
            Ticket.status == "assigned",
        )
        .all()
    )
    assert len(routes_b) == 0, "Student B không được thấy route của Student A"


# ── Test 5: Driver RBAC ───────────────────────────────────────────────────────
def test_rbac_driver_sees_own_vehicle_route(db):
    """
    Tài xế chỉ thấy tuyến được gán cho xe của mình.
    """
    ids = _seed_base(db)
    other_driver_id = str(uuid.uuid4())
    other_vehicle_id = str(uuid.uuid4())
    db.add(Profile(id=other_driver_id, role="driver", full_name="Driver B"))
    db.add(Vehicle(id=other_vehicle_id, license_plate="66A-99999", capacity=30, driver_id=other_driver_id))

    run_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()

    # Route gán cho xe của Driver A
    route_a_id = str(uuid.uuid4())
    db.add(Route(
        id=route_a_id,
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        vehicle_id=ids["vehicle_id"],
        status="pending",
        total_distance=5.0,
    ))
    # Route gán cho xe của Driver B
    route_b_id = str(uuid.uuid4())
    db.add(Route(
        id=route_b_id,
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        vehicle_id=other_vehicle_id,
        status="pending",
        total_distance=3.0,
    ))
    db.commit()

    # Driver A chỉ thấy route_a
    driver_a_routes = (
        db.query(Route)
        .join(Vehicle, Vehicle.id == Route.vehicle_id)
        .filter(Vehicle.driver_id == ids["driver_id"])
        .all()
    )
    assert len(driver_a_routes) == 1
    assert str(driver_a_routes[0].id) == route_a_id

    # Driver B chỉ thấy route_b
    driver_b_routes = (
        db.query(Route)
        .join(Vehicle, Vehicle.id == Route.vehicle_id)
        .filter(Vehicle.driver_id == other_driver_id)
        .all()
    )
    assert len(driver_b_routes) == 1
    assert str(driver_b_routes[0].id) == route_b_id


# ── Test 6: Job idempotency — chạy 2 lần không tạo route trùng ───────────────
def test_route_job_no_duplicate_on_rerun(db):
    """
    Worker nhận job đã SUCCEEDED → trả về ngay, không sinh route mới.
    Idempotency: một job/service_date/session/trip_type chỉ sinh 1 lần.
    """
    ids = _seed_base(db)
    run_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=5)).date()

    ticket = Ticket(
        id=str(uuid.uuid4()),
        user_id=ids["student_id"],
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=ids["pickup_id"],
        qr_code="QR_IDEM_001",
        status="reserved",
    )
    job_id_str = str(uuid.uuid4())
    job = RouteJob(
        id=job_id_str,
        service_date=run_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=ids["depot_id"],
        status="queued",
    )
    db.add_all([ticket, job])
    db.commit()

    # Lần 1
    result1 = run_route_job_worker(db=db, job_id=uuid.UUID(job_id_str))
    assert result1.status == "succeeded"

    route_count_1 = db.query(Route).filter(
        Route.service_date == run_date,
        Route.session_id == "MORNING_1",
    ).count()
    assert route_count_1 >= 1

    # Lần 2 — job đã SUCCEEDED → worker trả về sớm không làm gì
    result2 = run_route_job_worker(db=db, job_id=uuid.UUID(job_id_str))
    assert result2.status == "succeeded"

    route_count_2 = db.query(Route).filter(
        Route.service_date == run_date,
        Route.session_id == "MORNING_1",
    ).count()
    assert route_count_2 == route_count_1, (
        f"Chạy worker lần 2 không được tạo thêm route: "
        f"lần 1={route_count_1}, lần 2={route_count_2}"
    )
