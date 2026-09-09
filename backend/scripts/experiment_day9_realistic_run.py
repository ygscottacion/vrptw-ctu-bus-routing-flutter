"""
experiment_day9_realistic_run.py — Practical routing experiment script (Day 9)

Runs a realistic CTU bus routing job with ~40 student bookings unevenly distributed
across 8 pickup locations in Can Tho city, served by 4 vehicles with varying capacities.

Usage:
    cd backend
    python scripts/experiment_day9_realistic_run.py
"""

import datetime
import os
import sys
import uuid

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

from typing import Dict, List

# Ensure backend directory is in python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import event, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sqlite3

sqlite3.register_adapter(uuid.UUID, lambda u: str(u))
sqlite3.register_converter("VARCHAR", lambda b: b.decode())

from app.core.timezone import VN_TZ
from app.core.database import Base
from app.models.location import Location
from app.models.profile import Profile, ProfileRole
from app.models.route import Route, RouteStatus, RouteStop
from app.models.route_job import RouteJob, RouteJobStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.vehicle import Vehicle
from app.services.route_worker import run_route_job_worker
import app.services.route_worker as rw
from app.services.vrptw_solver import VRPTWSolverService

class FastVRPTWSolverService(VRPTWSolverService):
    def __init__(self, *args, **kwargs):
        super().__init__(use_static_matrix=True)
        self.routing_service.tabu_optimizer.max_iterations = 20


rw.VRPTWSolverService = FastVRPTWSolverService



def build_experiment_database():
    """Create an isolated SQLite in-memory database with auth schema attached."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False, "detect_types": sqlite3.PARSE_COLNAMES},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def attach_auth_schema(dbapi_connection, connection_record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS auth")

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()



def seed_realistic_ctu_dataset(db):
    """Seed ~40 student bookings across 8 realistic Can Tho locations."""
    service_date = (datetime.datetime.now(VN_TZ) + datetime.timedelta(days=1)).date()

    # 1. Create Drivers & Vehicles (4 vehicles with different capacities)
    vehicle_configs = [
        ("65B-016.11", 16, "Tài xế Nguyễn Văn 16 chỗ"),
        ("65B-029.22", 29, "Tài xế Trần Văn 29 chỗ A"),
        ("65B-029.33", 29, "Tài xế Lê Văn 29 chỗ B"),
        ("65B-045.44", 45, "Tài xế Phạm Văn 45 chỗ"),
    ]
    vehicles = []
    for plate, cap, driver_name in vehicle_configs:
        driver = Profile(id=uuid.uuid4(), role=ProfileRole.DRIVER, full_name=driver_name)
        db.add(driver)
        db.flush()

        veh = Vehicle(id=uuid.uuid4(), license_plate=plate, capacity=cap, driver_id=driver.id)
        db.add(veh)
        vehicles.append(veh)
    db.flush()

    # 2. Create Depot (CTU Campus 2) and 8 Pickup Stations
    depot = Location(
        id=uuid.uuid4(),
        name="Đại học Cần Thơ - Khu II (Depot chính)",
        latitude=10.0302,
        longitude=105.7721,
    )
    db.add(depot)

    stations = [
        {"name": "Trạm 1: Đường 3/2 (Cầu Đầu Sấu)", "lat": 10.0225, "lon": 105.7650, "booking_count": 8},
        {"name": "Trạm 2: Mậu Thân (Ngã 4 Nguyễn Văn Cừ)", "lat": 10.0360, "lon": 105.7680, "booking_count": 10},
        {"name": "Trạm 3: Xuân Khánh (Đường 30/4)", "lat": 10.0280, "lon": 105.7780, "booking_count": 6},
        {"name": "Trạm 4: Nguyễn Văn Linh (KDC 91B)", "lat": 10.0210, "lon": 105.7550, "booking_count": 7},
        {"name": "Trạm 5: Hùng Vương (Bến xe cũ)", "lat": 10.0450, "lon": 105.7820, "booking_count": 4},
        {"name": "Trạm 6: Ninh Kiều (Bến Ninh Kiều)", "lat": 10.0340, "lon": 105.7880, "booking_count": 3},
        {"name": "Trạm 7: Cái Răng (Cầu Cái Răng)", "lat": 10.0020, "lon": 105.7480, "booking_count": 2},
        {"name": "Trạm 8: Phong Điền (Ngã 3 Phong Điền)", "lat": 9.9850, "lon": 105.6950, "booking_count": 2},
    ]

    total_tickets = 0
    created_tickets = []
    pickup_locations = []

    for station in stations:
        count = station["booking_count"]
        for idx in range(count):
            total_tickets += 1
            # Add minor coordinate dispersion per student pickup point (simulate nearby street spots)
            loc = Location(
                id=uuid.uuid4(),
                name=f"{station['name']} - Điểm đón #{idx+1}",
                latitude=station["lat"] + (idx * 0.0001),
                longitude=station["lon"] + (idx * 0.0001),
                demand=1,
                time_window_start=datetime.datetime.combine(service_date, datetime.time(6, 0)),
                time_window_end=datetime.datetime.combine(service_date, datetime.time(7, 30)),
            )
            db.add(loc)
            db.flush()
            pickup_locations.append(loc)

            student = Profile(
                id=uuid.uuid4(),
                role=ProfileRole.PASSENGER,
                full_name=f"Sinh viên #{total_tickets} ({station['name']})",
            )
            db.add(student)
            db.flush()

            ticket = Ticket(
                id=uuid.uuid4(),
                user_id=student.id,
                service_date=service_date,
                session_id="MORNING_1",
                trip_type="pickup",
                pickup_location_id=loc.id,
                qr_code=f"QR_EXP_DAY9_{total_tickets}_{uuid.uuid4().hex[:6].upper()}",
                status=TicketStatus.RESERVED,
            )
            db.add(ticket)
            created_tickets.append(ticket)

    db.commit()

    return {
        "service_date": service_date,
        "depot": depot,
        "vehicles": vehicles,
        "tickets": created_tickets,
        "stations": stations,
        "total_tickets": total_tickets,
    }


def run_experiment():
    print("=" * 80)
    print("  KỊCH BẢN THỰC NGHIỆM T9 — ROUTING/SCHEDULER (DUY)")
    print("=" * 80)

    db = build_experiment_database()
    data = seed_realistic_ctu_dataset(db)

    print(f"\n[1] Khởi tạo dữ liệu thực nghiệm:")
    print(f"    - Ngày dịch vụ      : {data['service_date']}")
    print(f"    - Ca chạy            : MORNING_1 (pickup)")
    print(f"    - Depot chính        : {data['depot'].name} ({data['depot'].latitude}, {data['depot'].longitude})")
    print(f"    - Số lượng xe buýt  : {len(data['vehicles'])} xe (sức chứa: {[v.capacity for v in data['vehicles']]})")
    print(f"    - Tổng số sinh viên  : {data['total_tickets']} véĐặt (status = RESERVED)")
    print("    - Phân bố trạm đón   :")
    for st in data["stations"]:
        print(f"        * {st['name']:<42}: {st['booking_count']} sinh viên")

    # Create RouteJob
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

    print(f"\n[2] Thực thi Job phân tuyến `run_route_job_worker` (Job ID: {job.id})...")
    start_time = datetime.datetime.now()
    completed_job = run_route_job_worker(db=db, job_id=job.id)
    elapsed_sec = (datetime.datetime.now() - start_time).total_seconds()

    print(f"\n[3] Kết quả thực thi Job:")
    print(f"    - Trạng thái Job     : {completed_job.status}")
    print(f"    - Thời gian tính toán: {elapsed_sec:.3f} giây")
    if completed_job.error_message:
        print(f"    - Lỗi chi tiết       : {completed_job.error_message}")

    assert completed_job.status == RouteJobStatus.SUCCEEDED, "Job phân tuyến thất bại!"

    # Fetch created routes
    routes = db.query(Route).filter(Route.route_job_id == job.id).all()
    print(f"\n[4] Chi tiết các Tuyến Xe đã sinh ra ({len(routes)} tuyến):")
    print("-" * 80)

    assigned_tickets_count = 0
    vehicle_lookup: Dict[str, Vehicle] = {str(v.id): v for v in data["vehicles"]}

    anomalies = []

    for idx, route in enumerate(routes, 1):
        veh = vehicle_lookup.get(str(route.vehicle_id))
        stops = db.query(RouteStop).filter(RouteStop.route_id == route.id).order_by(RouteStop.stop_order).all()
        tickets_on_route = db.query(Ticket).filter(Ticket.route_id == route.id).all()
        assigned_tickets_count += len(tickets_on_route)

        cap = veh.capacity if veh else 0
        pax = len(tickets_on_route)
        utilization = (pax / cap * 100) if cap > 0 else 0

        print(f"\n  Tuyến #{idx}: Route ID = {route.id}")
        print(f"  Xe gán     : {veh.license_plate if veh else 'N/A'} (Sức chứa: {cap} chỗ)")
        print(f"  Hành khách : {pax}/{cap} SV ({utilization:.1f}% công suất)")
        print(f"  Quãng đường: {route.total_distance:.2f} km")
        print(f"  Danh sách trạm dừng ({len(stops)} trạm):")

        prev_order = 0
        for st in stops:
            loc = db.query(Location).filter(Location.id == st.location_id).first()
            arr_str = st.arrival_time.strftime("%H:%M:%S") if st.arrival_time else "N/A"
            loc_name = loc.name if loc else str(st.location_id)
            print(f"    - Stop #{st.stop_order:02d}: {loc_name:<50} (Đến: {arr_str})")

            # Check stop sequence continuity
            if st.stop_order != prev_order + 1:
                anomalies.append(f"Tuyến {route.id}: stop_order nhảy cóc ({prev_order} -> {st.stop_order})")
            prev_order = st.stop_order

        # Capacity check
        if pax > cap:
            anomalies.append(f"Tuyến {route.id}: Quá tải xe ({pax} > {cap})")
        if pax <= 3:
            anomalies.append(f"Tuyến {route.id}: Xe chạy ít sinh viên ({pax} SV)")

    print("\n" + "=" * 80)
    print("  XÁC NHẬN DỮ LIỆU GÁN TUYẾN (MANUAL VERIFICATION CHECKS)")
    print("=" * 80)

    # Check 1: Stop Order Continuity
    print("  [✓] Check 1: Thứ tự stop_order tăng liên tục 1, 2, 3...:", "ĐẠT" if not any("stop_order" in a for a in anomalies) else "THẤT BẠI")

    # Check 2: Vehicle Capacity Compliance
    print("  [✓] Check 2: Xe gán có capacity >= tổng SV trên tuyến   :", "ĐẠT" if not any("Quá tải" in a for a in anomalies) else "THẤT BẠI")

    # Check 3: Student Ticket Status Transition
    reserved_remaining = db.query(Ticket).filter(Ticket.service_date == data["service_date"], Ticket.status == TicketStatus.RESERVED).count()
    assigned_total = db.query(Ticket).filter(Ticket.service_date == data["service_date"], Ticket.status == TicketStatus.ASSIGNED).count()

    print(f"  [✓] Check 3: Chuyển trạng thái vé từ RESERVED -> ASSIGNED:")
    print(f"      - Vé RESERVED còn sót  : {reserved_remaining} vé (Kỳ vọng: 0)")
    print(f"      - Vé ASSIGNED đã gán  : {assigned_total}/{data['total_tickets']} vé (Kỳ vọng: {data['total_tickets']})")
    assert reserved_remaining == 0, f"Còn {reserved_remaining} vé chưa được gán!"
    assert assigned_total == data["total_tickets"], f"Chỉ gán được {assigned_total}/{data['total_tickets']} vé!"

    print("\n  [!] Ghi nhận các trường hợp đặc biệt / giới hạn thực tế (Known Limits Input):")
    if anomalies:
        for a in anomalies:
            print(f"      - {a}")
    else:
        print("      - Không phát hiện bất thường nghiêm trọng. Các tuyến gom cụm hợp lý theo khu vực địa lý.")

    print("\n" + "=" * 80)
    print("  THỰC NGHIỆM T9 HOÀN THÀNH THÀNH CÔNG!")
    print("=" * 80)


if __name__ == "__main__":
    run_experiment()
