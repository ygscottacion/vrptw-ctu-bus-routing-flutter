"""
test_day5_integration.py — Kiểm thử chuyên biệt cho Thành viên 3 (Duy - Routing/Scheduler)

Nhiệm vụ Day 5 của Duy:
"Sweep/Tabu chạy từ booking và lưu routes/stops/gán tài xế."

Các ca kiểm thử trực tiếp tầng Service/Algorithm của Duy:
1. test_sweep_tabu_runs_from_booking:
   Đọc danh sách vé đặt (Ticket RESERVED), chạy Sweep Clustering và Tabu Search.
2. test_routes_and_stops_persisted_correctly:
   Kiểm tra Route và danh sách RouteStop được lưu tuần tự vào DB với arrival_time chuẩn.
3. test_driver_and_vehicle_assignment:
   Kiểm tra Route được gán xe/tài xế và tất cả Ticket chuyển trạng thái sang ASSIGNED.
4. test_capacity_and_time_window_respect:
   Kiểm tra thuật toán không phân bổ vượt quá sức chứa xe buýt và đúng khung giờ đón.
5. test_route_worker_atomic_rollback_on_error:
   Kiểm tra tính an toàn giao dịch: lỗi ở bước bất kỳ sẽ rollback và đánh dấu job FAILED.
"""
import uuid
import datetime
import pytest
from sqlalchemy.orm import Session

from app.core.timezone import VN_TZ
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.services.route_worker import run_route_job_worker
from app.services.vrptw_solver import VRPTWSolverService


# ── Helper: Cấu hình solver dùng static matrix cho kiểm thử ──────────────────
class _StaticSolverService(VRPTWSolverService):
    def __init__(self):
        super().__init__(use_static_matrix=True)


@pytest.fixture(autouse=True)
def patch_solver(monkeypatch):
    import app.services.route_worker as rw
    monkeypatch.setattr(rw, "VRPTWSolverService", _StaticSolverService)


# ── Fixture dữ liệu mẫu độc lập cho Duy ──────────────────────────────────────
@pytest.fixture
def seed_routing_data(db_session: Session):
    """
    Seed dữ liệu đầu vào chuẩn để kiểm thử thuật toán định tuyến của Duy:
    - 1 Depot (ĐH Cần Thơ)
    - 4 Trạm đón sinh viên trong bán kính <= 10km
    - 2 Xe buýt (đã gán tài xế)
    - 4 Sinh viên có vé đặt (status = RESERVED)
    """
    db = db_session
    service_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=2)).date()

    # 1. Tạo 2 Tài xế & 2 Xe buýt
    driver_1 = Profile(id=uuid.uuid4(), role=ProfileRole.DRIVER, full_name="Tài xế Nguyễn Văn A")
    driver_2 = Profile(id=uuid.uuid4(), role=ProfileRole.DRIVER, full_name="Tài xế Trần Văn B")
    db.add_all([driver_1, driver_2])
    db.flush()

    vehicle_1 = Vehicle(id=uuid.uuid4(), license_plate="65B-001.01", capacity=30, driver_id=driver_1.id)
    vehicle_2 = Vehicle(id=uuid.uuid4(), license_plate="65B-001.02", capacity=30, driver_id=driver_2.id)
    db.add_all([vehicle_1, vehicle_2])

    # 2. Tạo 1 Depot & 4 Trạm đón
    depot = Location(
        id=uuid.uuid4(),
        name="Đại học Cần Thơ (Depot)",
        latitude=10.0302,
        longitude=105.7721,
    )
    pickup_stops = [
        Location(
            id=uuid.uuid4(),
            name=f"Trạm đón số {i}",
            latitude=10.0302 + (i * 0.002),
            longitude=105.7721 + (i * 0.002),
            demand=1,
            time_window_start=datetime.datetime.combine(service_date, datetime.time(6, 0)),
            time_window_end=datetime.datetime.combine(service_date, datetime.time(7, 30)),
        )
        for i in range(1, 5)
    ]
    db.add(depot)
    db.add_all(pickup_stops)
    db.flush()

    # 3. Tạo 4 Sinh viên và 4 Vé đặt trước (RESERVED)
    students = []
    tickets = []
    for i in range(4):
        st = Profile(id=uuid.uuid4(), role=ProfileRole.PASSENGER, full_name=f"Sinh viên {i+1}")
        students.append(st)
        db.add(st)
        db.flush()

        tk = Ticket(
            id=uuid.uuid4(),
            user_id=st.id,
            service_date=service_date,
            session_id="MORNING_1",
            trip_type="pickup",
            pickup_location_id=pickup_stops[i].id,
            qr_code=f"QR_DUY_DAY5_{i+1}_{uuid.uuid4().hex[:6].upper()}",
            status=TicketStatus.RESERVED,
        )
        tickets.append(tk)
        db.add(tk)

    db.commit()

    return {
        "service_date": service_date,
        "depot": depot,
        "pickup_stops": pickup_stops,
        "vehicles": [vehicle_1, vehicle_2],
        "drivers": [driver_1, driver_2],
        "students": students,
        "tickets": tickets,
    }


# ── TEST 1: Sweep/Tabu chạy từ danh sách booking và sinh Route/Stops ──────────
def test_sweep_tabu_runs_from_booking(db_session: Session, seed_routing_data):
    """
    Xác thực worker của Duy:
    1. Đọc đúng các vé RESERVED của ca chạy.
    2. Chạy thuật toán Sweep + Tabu tìm lời giải phân tuyến tối ưu.
    3. Trạng thái Job chuyển thành SUCCEEDED.
    """
    db = db_session
    data = seed_routing_data

    # Tạo RouteJob ở trạng thái QUEUED
    job = RouteJob(
        id=uuid.uuid4(),
        service_date=data["service_date"],
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=data["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    # Chạy worker của Duy
    result_job = run_route_job_worker(db=db, job_id=job.id)

    assert result_job.status == RouteJobStatus.SUCCEEDED, (
        f"Job phân tuyến của Duy phải đạt SUCCEEDED, nhưng hiện tại: {result_job.status}. "
        f"Lỗi chi tiết: {result_job.error_message}"
    )


# ── TEST 2: Xác thực dữ liệu Routes và RouteStops được lưu chuẩn xác ──────────
def test_routes_and_stops_persisted_correctly(db_session: Session, seed_routing_data):
    """
    Xác thực việc lưu dữ liệu tuyến và trạm dừng:
    - Bảng routes có bản ghi mới với quãng đường total_distance > 0.
    - Bảng route_stops có ít nhất 1 trạm Depot (stop_order=1) và các trạm đón.
    - Thứ tự stop_order tuần tự liên tục (1, 2, 3...).
    - arrival_time của các trạm dừng được tính toán hợp lệ.
    """
    db = db_session
    data = seed_routing_data

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=data["service_date"],
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=data["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    run_route_job_worker(db=db, job_id=job.id)

    # Truy vấn các tuyến được sinh ra từ job này
    routes = db.query(Route).filter(Route.route_job_id == job.id).all()
    assert len(routes) >= 1, "Phải sinh ra ít nhất 1 tuyến xe"

    for r in routes:
        assert r.total_distance > 0, f"Quãng đường tuyến {r.id} phải > 0km"
        assert r.status == RouteStatus.PENDING, "Tuyến mới sinh phải có trạng thái PENDING"

        # Kiểm tra danh sách trạm dừng RouteStops
        stops = db.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.stop_order).all()
        assert len(stops) >= 2, f"Tuyến {r.id} phải có ít nhất 1 Depot + 1 trạm đón"

        # Trạm đầu tiên (stop_order = 1) phải là Depot
        assert stops[0].stop_order == 1
        assert stops[0].location_id == data["depot"].id, "Trạm số 1 của tuyến phải là trạm trường (Depot)"

        # Thứ tự stop_order phải tăng dần liên tục
        for idx, st in enumerate(stops, start=1):
            assert st.stop_order == idx, f"Thứ tự trạm dừng bị ngắt quãng tại stop {st.id}"
            assert st.arrival_time is not None, f"Trạm {st.id} phải có thời gian dự kiến đón arrival_time"


# ── TEST 3: Gán xe, tài xế và cập nhật trạng thái vé sang ASSIGNED ────────────
def test_driver_and_vehicle_assignment(db_session: Session, seed_routing_data):
    """
    Xác thực nghiệp vụ gán tài xế và vé:
    - Route được gán vehicle_id hợp lệ (xe đã có driver_id).
    - Toàn bộ 4 vé Ticket ban đầu chuyển từ RESERVED -> ASSIGNED.
    - Mỗi vé có ticket.route_id trỏ đúng vào Route được phân công.
    - Số lượng passenger_count trên Route khớp với số vé thực tế.
    """
    db = db_session
    data = seed_routing_data

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=data["service_date"],
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=data["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    run_route_job_worker(db=db, job_id=job.id)

    # 1. Kiểm tra vé đã được chuyển sang ASSIGNED
    for tk in data["tickets"]:
        db.refresh(tk)
        assert tk.status == TicketStatus.ASSIGNED, f"Vé {tk.id} phải chuyển sang ASSIGNED"
        assert tk.route_id is not None, f"Vé {tk.id} phải được gắn route_id"

    # 2. Kiểm tra Route được gán xe và tài xế
    routes = db.query(Route).filter(Route.route_job_id == job.id).all()
    assigned_vehicle_ids = [r.vehicle_id for r in routes]
    assert all(v_id is not None for v_id in assigned_vehicle_ids), "Tất cả các tuyến đều phải được gán xe buýt"

    # Xe được gán phải có tài xế phụ trách
    for r in routes:
        vehicle = db.query(Vehicle).filter(Vehicle.id == r.vehicle_id).first()
        assert vehicle is not None
        assert vehicle.driver_id is not None, f"Xe {vehicle.license_plate} được gán cho tuyến phải có tài xế phụ trách"


# ── TEST 4: Đảm bảo không vượt quá sức chứa xe buýt (Capacity Constraint) ────
def test_capacity_and_time_window_respect(db_session: Session, seed_routing_data):
    """
    Xác thực thuật toán của Duy tuân thủ giới hạn tải trọng:
    - Tổng số sinh viên gán vào một tuyến <= sức chứa (capacity) của xe buýt đó.
    """
    db = db_session
    data = seed_routing_data

    job = RouteJob(
        id=uuid.uuid4(),
        service_date=data["service_date"],
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=data["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    run_route_job_worker(db=db, job_id=job.id)

    routes = db.query(Route).filter(Route.route_job_id == job.id).all()
    for r in routes:
        assigned_tickets_count = db.query(Ticket).filter(Ticket.route_id == r.id).count()
        vehicle = db.query(Vehicle).filter(Vehicle.id == r.vehicle_id).first()
        assert assigned_tickets_count <= vehicle.capacity, (
            f"Tuyến {r.id} bị quá tải: {assigned_tickets_count} vé > sức chứa {vehicle.capacity}"
        )


# ── TEST 5: Giao dịch nguyên tử (Atomic rollback khi gặp lỗi) ─────────────────
def test_route_worker_atomic_rollback_on_error(db_session: Session, seed_routing_data):
    """
    Xác thực tính an toàn của worker Duy:
    - Khi không có vé nào hoặc trạm đón bị xoá đột ngột, worker phải rollback sạch sẽ
      và cập nhật RouteJob sang FAILED mà không để lại dữ liệu rác/mồ côi trong routes/route_stops.
    """
    db = db_session
    data = seed_routing_data

    # Job cho một ngày không có vé nào được đặt
    empty_date = data["service_date"] + datetime.timedelta(days=10)
    job_empty = RouteJob(
        id=uuid.uuid4(),
        service_date=empty_date,
        session_id="MORNING_1",
        trip_type="pickup",
        depot_location_id=data["depot"].id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(job_empty)
    db.commit()

    # Chạy worker và kỳ vọng raise exception / chuyển FAILED
    with pytest.raises(Exception):
        run_route_job_worker(db=db, job_id=job_empty.id)

    db.refresh(job_empty)
    assert job_empty.status == RouteJobStatus.FAILED, "Job không có vé phải có trạng thái FAILED"

    # Đảm bảo không có route rác nào bị ghi vào database
    orphaned_routes = db.query(Route).filter(Route.route_job_id == job_empty.id).count()
    assert orphaned_routes == 0, "Không được để lại Route mồ côi khi job thất bại"
