import os
import sys
from datetime import datetime, timedelta

# Thêm thư mục hiện tại vào PYTHONPATH để import được các module của FastAPI
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.vehicle import Vehicle
from app.models.location import Location
from app.models.incident import Incident
from app.models.user import User

def seed_data():
    db = SessionLocal()
    try:
        print("Bắt đầu tạo dữ liệu mẫu (Mock Data)...")

        # 1. Kiểm tra và lấy ID của admin để gán làm tài xế tạm
        admin_user = db.query(User).filter(User.username == "admin").first()
        driver_id = admin_user.id if admin_user else 1

        # 2. Tạo dữ liệu Xe buýt (Vehicles)
        if not db.query(Vehicle).first():
            print("- Đang tạo Xe buýt...")
            v1 = Vehicle(license_plate='65B-123.45', capacity=45, status='active', current_latitude=10.0305, current_longitude=105.7684)
            v2 = Vehicle(license_plate='65B-999.99', capacity=30, status='active', current_latitude=10.0290, current_longitude=105.7700)
            db.add_all([v1, v2])
        
        # 3. Tạo dữ liệu Trạm dừng (Locations) - Phục vụ thuật toán Sinh Tuyến
        if not db.query(Location).first():
            print("- Đang tạo Trạm dừng...")
            l1 = Location(name='Depot ĐH Cần Thơ', latitude=10.0299, longitude=105.7706, demand=0, time_window_start='06:00', time_window_end='18:00')
            l2 = Location(name='Ký Túc Xá A', latitude=10.0310, longitude=105.7680, demand=5, time_window_start='06:00', time_window_end='18:00')
            l3 = Location(name='Khoa CNTT', latitude=10.0305, longitude=105.7695, demand=3, time_window_start='07:00', time_window_end='17:00')
            l4 = Location(name='Khu 2 - Cổng A', latitude=10.0285, longitude=105.7715, demand=8, time_window_start='06:00', time_window_end='18:00')
            l5 = Location(name='Khoa Nông Nghiệp', latitude=10.0325, longitude=105.7675, demand=4, time_window_start='07:00', time_window_end='17:00')
            db.add_all([l1, l2, l3, l4, l5])
            
        # 4. Tạo dữ liệu Sự cố (Incidents)
        if not db.query(Incident).first():
            print("- Đang tạo Sự cố...")
            now = datetime.utcnow()
            i1 = Incident(title='Bể lốp xe', description='Xe 65B-123.45 bị cán đinh ở đường 3/2', status='pending', reported_at=now, driver_id=driver_id)
            i2 = Incident(title='Tắc đường nghiêm trọng', description='Kẹt xe ngã tư Mậu Thân, xe di chuyển rất chậm.', status='in_progress', reported_at=now - timedelta(hours=1), driver_id=driver_id)
            db.add_all([i1, i2])
            
        db.commit()
        print("✅ Đã chèn dữ liệu mẫu thành công! Bạn có thể làm mới trang Web để xem kết quả.")
    except Exception as e:
        print("❌ Có lỗi xảy ra:", str(e))
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
