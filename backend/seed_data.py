"""
Seed data script for CTU Bus Routing System
Adds initial Users, Vehicles, Depot and Location stops around Can Tho City.
"""
from app.core.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.route import Route, RouteStop
from app.models.ticket import Ticket
from app.models.incident import Incident
from app.core.security import get_password_hash

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

#SeedPassword = 'TestPassword123!'
def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("[INFO] Seeding Database...")

        # 1. Seed Users
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                full_name="Quản trị viên CTU",
                phone="0901234567"
            )
            driver1 = User(
                username="driver1",
                password_hash=get_password_hash("driver123"),
                role=UserRole.DRIVER,
                full_name="Tài xế Nguyễn Văn A",
                phone="0918123456"
            )
            driver2 = User(
                username="driver2",
                password_hash=get_password_hash("driver123"),
                role=UserRole.DRIVER,
                full_name="Tài xế Trần Văn B",
                phone="0918654321"
            )
            student1 = User(
                username="student1",
                password_hash=get_password_hash("student123"),
                role=UserRole.PASSENGER,
                full_name="Sinh viên Lê Văn C",
                phone="0939123456"
            )
            db.add_all([admin, driver1, driver2, student1])
            db.commit()
            print("✅ Users seeded: admin (pass: admin123), driver1, driver2 (pass: driver123), student1 (pass: student123)")

        # 2. Seed Depot & Locations (Can Tho Coordinates)
        if not db.query(Location).first():
            depot = Location(name="Depot - ĐH Cần Thơ (Khu II)", latitude=10.0299, longitude=105.7684, demand=0)
            loc1 = Location(name="Trạm 1 - Bến Ninh Kiều", latitude=10.0342, longitude=105.7876, demand=5)
            loc2 = Location(name="Trạm 2 - Chợ Cái Răng", latitude=10.0031, longitude=105.7482, demand=8)
            loc3 = Location(name="Trạm 3 - Công viên Sông Hậu", latitude=10.0461, longitude=105.7891, demand=6)
            loc4 = Location(name="Trạm 4 - Siêu thị Lotte Mart", latitude=10.0402, longitude=105.7621, demand=10)
            loc5 = Location(name="Trạm 5 - Bệnh viện ĐKTW Cần Thơ", latitude=10.0215, longitude=105.7531, demand=7)
            loc6 = Location(name="Trạm 6 - Chợ Đêm Trần Phú", latitude=10.0435, longitude=105.7820, demand=4)
            loc7 = Location(name="Trạm 7 - Siêu thị GO! Cần Thơ", latitude=10.0156, longitude=105.7645, demand=9)
            loc8 = Location(name="Trạm 8 - Bến Xe Trung Tâm Cần Thơ", latitude=10.0078, longitude=105.7721, demand=12)
            loc9 = Location(name="Trạm 9 - ĐH Y Dược Cần Thơ", latitude=10.0265, longitude=105.7580, demand=6)
            loc10 = Location(name="Trạm 10 - Công viên Cầu Cần Thơ", latitude=10.0102, longitude=105.7950, demand=5)

            db.add_all([depot, loc1, loc2, loc3, loc4, loc5, loc6, loc7, loc8, loc9, loc10])
            db.commit()
            print("✅ Locations seeded (CTU Depot + 10 Bus Stops)")

        # 3. Seed Vehicles
        if not db.query(Vehicle).first():
            driver1_obj = db.query(User).filter(User.username == "driver1").first()
            driver2_obj = db.query(User).filter(User.username == "driver2").first()

            v1 = Vehicle(license_plate="65B-012.34", capacity=20, driver_id=driver1_obj.id if driver1_obj else None)
            v2 = Vehicle(license_plate="65B-056.78", capacity=25, driver_id=driver2_obj.id if driver2_obj else None)

            db.add_all([v1, v2])
            db.commit()
            print("✅ Vehicles seeded: 65B-012.34, 65B-056.78")

        print("🎉 Database Seeding Completed Successfully!")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
