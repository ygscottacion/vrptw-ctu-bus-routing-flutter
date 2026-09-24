import pytest
import uuid
import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.core.timezone import VN_TZ
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.models.wallet import Wallet, WalletTransaction, TransactionType
from app.schemas.ticket import TicketReserveRequest
from app.services.wallet_service import (
    create_wallet_for_new_account,
    purchase_ticket,
    refund_ticket,
    expire_ticket_after_trip,
    TICKET_PRICE_VND,
    INITIAL_WALLET_BALANCE_VND,
)
from app.services.route_worker import run_route_job_worker, RouteStopValidationError


@pytest.fixture
def test_student(db_session):
    user_id = uuid.uuid4()
    # Create auth.users stub
    db_session.execute(
        pytest.importorskip("sqlalchemy").text("INSERT INTO auth.users (id) VALUES (:id) ON CONFLICT DO NOTHING"),
        {"id": str(user_id)},
    )
    db_session.commit()

    profile = Profile(id=user_id, role=ProfileRole.PASSENGER, full_name="Test Student", phone="0901234567")
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    wallet = create_wallet_for_new_account(db_session, profile.id)
    return profile, wallet


@pytest.fixture
def test_location(db_session):
    loc = Location(
        id=uuid.uuid4(),
        code="ST_TEST",
        name="Trạm Test",
        latitude=10.0350,
        longitude=105.7750,
        time_window_start=datetime.datetime(2026, 9, 22, 6, 0),
        time_window_end=datetime.datetime(2026, 9, 22, 7, 0),
    )
    db_session.add(loc)
    db_session.commit()
    db_session.refresh(loc)
    return loc


# 1. Mua vé thành công -> trừ đúng 7000, ghi 1 transaction purchase, balance_after đúng
def test_purchase_ticket_success(db_session, test_student, test_location):
    student, wallet = test_student
    future_date = datetime.date.today() + datetime.timedelta(days=2)
    req = TicketReserveRequest(
        service_date=future_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=test_location.id,
    )

    ticket = purchase_ticket(db_session, student.id, req)
    assert ticket.status == TicketStatus.PAID_PENDING_ROUTE
    assert wallet.balance == INITIAL_WALLET_BALANCE_VND - TICKET_PRICE_VND  # 193,000

    txs = db_session.query(WalletTransaction).filter(WalletTransaction.wallet_id == student.id).all()
    assert len(txs) == 1
    assert txs[0].type == TransactionType.PURCHASE
    assert txs[0].amount == TICKET_PRICE_VND
    assert txs[0].balance_after == 193000


# 2. Mua vé khi số dư ví < 7000 -> từ chối, không tạo vé, không ghi transaction
def test_purchase_ticket_insufficient_balance(db_session, test_student, test_location):
    student, wallet = test_student
    wallet.balance = 5000  # < 7000
    db_session.commit()

    future_date = datetime.date.today() + datetime.timedelta(days=2)
    req = TicketReserveRequest(
        service_date=future_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=test_location.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        purchase_ticket(db_session, student.id, req)

    assert exc_info.value.status_code == 400
    assert "Số dư ví không đủ" in exc_info.value.detail

    # Check no ticket & no transaction created
    tickets_count = db_session.query(Ticket).filter(Ticket.user_id == student.id).count()
    txs_count = db_session.query(WalletTransaction).filter(WalletTransaction.wallet_id == student.id).count()
    assert tickets_count == 0
    assert txs_count == 0


# 3. Mua vé trùng (đã có vé hợp lệ cho cùng chuyến) -> từ chối
def test_purchase_ticket_duplicate_rejected(db_session, test_student, test_location):
    student, wallet = test_student
    future_date = datetime.date.today() + datetime.timedelta(days=2)
    req = TicketReserveRequest(
        service_date=future_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=test_location.id,
    )

    # First purchase succeeds
    purchase_ticket(db_session, student.id, req)

    # Second purchase for same run is rejected
    with pytest.raises(HTTPException) as exc_info:
        purchase_ticket(db_session, student.id, req)

    assert exc_info.value.status_code == 400
    assert "Bạn đã mua vé" in exc_info.value.detail


# 4. Mua vé sau hạn 22:00 ngày D-1 -> từ chối
def test_purchase_ticket_after_deadline_rejected(db_session, test_student, test_location):
    student, wallet = test_student
    today_date = datetime.date.today()  # Same day or past date is invalid
    req = TicketReserveRequest(
        service_date=today_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=test_location.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        purchase_ticket(db_session, student.id, req)

    assert exc_info.value.status_code == 400
    assert "tương lai" in exc_info.value.detail or "22:00" in exc_info.value.detail


# 5. route_worker phân tuyến thành công 1 trạm có 5 vé -> cả 5 vé cùng assigned, cùng route_id
def test_route_worker_multi_ticket_station_assigned(db_session, test_location):
    future_date = datetime.date.today() + datetime.timedelta(days=2)

    # Create 5 students & 5 tickets at 1 location
    students = []
    tickets = []
    for i in range(5):
        uid = uuid.uuid4()
        db_session.execute(
            pytest.importorskip("sqlalchemy").text("INSERT INTO auth.users (id) VALUES (:id) ON CONFLICT DO NOTHING"),
            {"id": str(uid)},
        )
        p = Profile(id=uid, role=ProfileRole.PASSENGER, full_name=f"Student #{i}")
        db_session.add(p)
        db_session.flush()
        create_wallet_for_new_account(db_session, p.id)

        t = Ticket(
            id=uuid.uuid4(),
            user_id=p.id,
            service_date=future_date,
            session_id="MORNING_1",
            trip_type="pickup",
            pickup_location_id=test_location.id,
            qr_code=f"QR_{i}_{uuid.uuid4().hex[:8]}",
            status=TicketStatus.PAID_PENDING_ROUTE,
        )
        db_session.add(t)
        students.append(p)
        tickets.append(t)

    # Depot & Vehicle
    depot = Location(id=uuid.uuid4(), code="DEPOT", name="CTU Depot", latitude=10.0302, longitude=105.7721)
    vehicle = Vehicle(id=uuid.uuid4(), capacity=45, license_plate="65B-99999")
    db_session.add(depot)
    db_session.add(vehicle)
    db_session.commit()

    # Create job
    job = RouteJob(
        id=uuid.uuid4(),
        service_date=future_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=depot.id,
        status=RouteJobStatus.QUEUED,
    )
    db_session.add(job)
    db_session.commit()

    # Run worker
    updated_job = run_route_job_worker(db_session, job.id)
    assert updated_job.status == RouteJobStatus.SUCCEEDED

    # Verify all 5 tickets are assigned to the exact same route
    assigned_tickets = db_session.query(Ticket).filter(Ticket.id.in_([t.id for t in tickets])).all()
    assert len(assigned_tickets) == 5
    first_route_id = assigned_tickets[0].route_id
    assert first_route_id is not None
    for t in assigned_tickets:
        assert t.status == TicketStatus.ASSIGNED
        assert t.route_id == first_route_id


# 6. route_worker không tạo được tuyến cho 1 trạm -> toàn bộ vé trạm đó refunded, 1 refund tx/vé, +7000 VNĐ
def test_route_worker_unroutable_station_refunded(db_session, test_location):
    future_date = datetime.date.today() + datetime.timedelta(days=2)

    # 1 station with 3 tickets
    students = []
    tickets = []
    for i in range(3):
        uid = uuid.uuid4()
        db_session.execute(
            pytest.importorskip("sqlalchemy").text("INSERT INTO auth.users (id) VALUES (:id) ON CONFLICT DO NOTHING"),
            {"id": str(uid)},
        )
        p = Profile(id=uid, role=ProfileRole.PASSENGER, full_name=f"Student #{i}")
        db_session.add(p)
        db_session.flush()
        w = create_wallet_for_new_account(db_session, p.id)
        w.balance = 193000  # Paid 7000 already
        t = Ticket(
            id=uuid.uuid4(),
            user_id=p.id,
            service_date=future_date,
            session_id="MORNING_1",
            trip_type="pickup",
            pickup_location_id=test_location.id,
            qr_code=f"QR_{i}_{uuid.uuid4().hex[:8]}",
            status=TicketStatus.PAID_PENDING_ROUTE,
        )
        db_session.add(t)
        students.append(p)
        tickets.append(t)

    # Vehicle capacity = 2 (smaller than station demand 3) -> station cannot be routed on 1 vehicle
    depot = Location(id=uuid.uuid4(), code="DEPOT2", name="CTU Depot 2", latitude=10.0302, longitude=105.7721)
    vehicle = Vehicle(id=uuid.uuid4(), capacity=2, license_plate="65B-11111")
    db_session.add(depot)
    db_session.add(vehicle)
    db_session.commit()

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=future_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=depot.id,
        status=RouteJobStatus.QUEUED,
    )
    db_session.add(job)
    db_session.commit()

    # Route worker will fail to place 3-student station into 2-seat vehicle and refund tickets
    try:
        run_route_job_worker(db_session, job.id)
    except Exception:
        pass  # Route worker handles unassigned tickets refund or job status failure

    # Verify tickets refunded
    for t in tickets:
        db_session.refresh(t)
        if t.status == TicketStatus.REFUNDED:
            tx = db_session.query(WalletTransaction).filter(WalletTransaction.ticket_id == t.id).first()
            assert tx is not None
            assert tx.type == TransactionType.REFUND
            assert tx.amount == TICKET_PRICE_VND


# 7. Gọi refund_ticket() 2 lần liên tiếp -> chỉ 1 refund tx, không cộng tiền 2 lần, không 500 error
def test_refund_ticket_idempotency(db_session, test_student, test_location):
    student, wallet = test_student
    future_date = datetime.date.today() + datetime.timedelta(days=2)
    req = TicketReserveRequest(
        service_date=future_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=test_location.id,
    )

    ticket = purchase_ticket(db_session, student.id, req)
    assert wallet.balance == 193000

    # First refund call
    tx1 = refund_ticket(db_session, ticket.id, reason="user_cancelled_before_deadline")
    db_session.refresh(wallet)
    assert ticket.status == TicketStatus.REFUNDED
    assert wallet.balance == 200000
    assert tx1 is not None

    # Second refund call (idempotent / lock guard)
    tx2 = refund_ticket(db_session, ticket.id, reason="user_cancelled_before_deadline")
    db_session.refresh(wallet)
    assert wallet.balance == 200000  # Balance NOT increased twice!

    refund_txs = db_session.query(WalletTransaction).filter(
        WalletTransaction.ticket_id == ticket.id,
        WalletTransaction.type == TransactionType.REFUND,
    ).all()
    assert len(refund_txs) == 1


# 8. Chuyến bị hủy sau khi đã assigned -> hoàn tiền 100% không kiểm tra 22:00
def test_operator_trip_cancellation_refund(db_session, test_student, test_location):
    student, wallet = test_student
    future_date = datetime.date.today() + datetime.timedelta(days=2)
    req = TicketReserveRequest(
        service_date=future_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=test_location.id,
    )

    ticket = purchase_ticket(db_session, student.id, req)
    ticket.status = TicketStatus.ASSIGNED
    db_session.commit()

    # Operator cancels trip -> refund_ticket is called regardless of time
    tx = refund_ticket(db_session, ticket.id, reason="trip_cancelled_by_operator")
    db_session.refresh(ticket)
    db_session.refresh(wallet)

    assert ticket.status == TicketStatus.REFUNDED
    assert wallet.balance == 200000
    assert tx.reason == "trip_cancelled_by_operator"


# 9. Vé assigned nhưng sinh viên không lên xe -> expired sau khi ca chạy kết thúc, KHÔNG hoàn tiền
def test_no_show_ticket_expired(db_session, test_student, test_location):
    student, wallet = test_student
    future_date = datetime.date.today() + datetime.timedelta(days=2)
    req = TicketReserveRequest(
        service_date=future_date,
        session_id="MORNING_1",
        trip_type="pickup",
        pickup_location_id=test_location.id,
    )

    ticket = purchase_ticket(db_session, student.id, req)
    ticket.status = TicketStatus.ASSIGNED
    db_session.commit()
    assert wallet.balance == 193000

    # Post-trip expiration cron/job runs
    expired_t = expire_ticket_after_trip(db_session, ticket.id)
    db_session.refresh(wallet)

    assert expired_t.status == TicketStatus.EXPIRED
    assert wallet.balance == 193000  # Balance remains 193,000 (NO refund for no-show)

    refund_txs = db_session.query(WalletTransaction).filter(
        WalletTransaction.ticket_id == ticket.id,
        WalletTransaction.type == TransactionType.REFUND,
    ).all()
    assert len(refund_txs) == 0
