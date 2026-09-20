"""
backend/scripts/seed_supabase.py
Chạy: SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... SEED_TEST_PASSWORD=... python -m scripts.seed_supabase
KHÔNG commit service-role key vào repo. Đọc từ biến môi trường / secret manager.
"""
import os
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

STUDENTS = [f"student{i}@test.example.com" for i in range(1, 6)]   # 5 student
DRIVERS  = [f"driver{i}@test.example.com" for i in range(1, 3)]    # 2 driver

# Mật khẩu dùng chung cho toàn bộ 7 tài khoản test (5 student + 2 driver).
# Giá trị THẬT đang dùng trên staging hiện tại: "TestPassword123!"
# (Xác nhận bằng cách test login qua Supabase Auth API — script chỉ TẠO MỚI
# nếu email chưa tồn tại (find_or_create_user), không update password cho
# user đã có, nên mọi lần chạy lại với SEED_TEST_PASSWORD khác giá trị ban
# đầu đều KHÔNG có tác dụng đổi password.)
#
# KHÔNG hardcode giá trị thật ở đây — đọc từ biến môi trường SEED_TEST_PASSWORD
# khi chạy script. Giá trị thật lưu trong 1Password/Bitwarden của team,
# không dán vào chat/commit/log. Muốn đổi mật khẩu cho tài khoản đã tồn tại
# cần thêm logic gọi update_user_by_id — script hiện tại chưa hỗ trợ.
TEST_PASSWORD = os.environ["SEED_TEST_PASSWORD"]

def find_or_create_user(email: str) -> str:
    """Tìm theo email trước, không tạo trùng khi chạy lại lần 2."""
    existing = client.auth.admin.list_users()
    for u in existing:
        if u.email == email:
            return u.id
    created = client.auth.admin.create_user({
        "email": email,
        "password": TEST_PASSWORD,
        "email_confirm": True,
    })
    return created.user.id

def main():
    student_ids = [find_or_create_user(e) for e in STUDENTS]
    driver_ids = [find_or_create_user(e) for e in DRIVERS]

    # Trigger on_auth_user_created đã tạo profile role=passenger cho tất cả.
    # Cập nhật đúng 2 profile driver bằng quyền admin (service role bypass RLS).
    for uid in driver_ids:
        client.table("profiles").update({"role": "driver"}).eq("id", uid).execute()

    # Upsert vehicle theo license_plate (natural key ổn định)
    vehicles = [
        {"license_plate": "51F-000.01", "driver_id": driver_ids[0]},
        {"license_plate": "51F-000.02", "driver_id": driver_ids[1]},
    ]
    client.table("vehicles").upsert(vehicles, on_conflict="license_plate").execute()

    # Upsert location theo natural key ổn định (code unique nếu tên không đủ ổn định)
    locations = [
        # --- DEPOT CHÍNH (Điểm xuất phát/kết thúc của xe) ---
        {
            "code": "LOC-01", 
            "name": "ĐH Cần Thơ - Khu II (Depot chính)", 
            "latitude": 10.0282, 
            "longitude": 105.7682, 
            "demand": 0
        },
        
        # --- 19 TRẠM ĐÓN KHÁCH BÊN NGOÀI ĐẠI HỌC CẦN THƠ ---
        {"code": "LOC-02", "name": "Bến Ninh Kiều", "latitude": 10.032213, "longitude": 105.787976, "demand": 2},
        {"code": "LOC-03", "name": "Bến xe Trung tâm Cần Thơ", "latitude": 10.005198, "longitude": 105.772084, "demand": 6},
        {"code": "LOC-04", "name": "Hẻm 51 - Hồ Búng Xán", "latitude": 10.024814, "longitude": 105.767565, "demand": 2},
        {"code": "LOC-05", "name": "ĐH Y Dược Cần Thơ", "latitude": 10.034498, "longitude": 105.755812, "demand": 4},
        {"code": "LOC-06", "name": "Bệnh viện Đa khoa thành phố Cần Thơ", "latitude": 10.030945, "longitude": 105.781573, "demand": 3},
        {"code": "LOC-07", "name": "TTTM Lotte Mart Cần Thơ", "latitude": 10.042212296099608, "longitude": 105.76656821978234, "demand": 3},
        {"code": "LOC-08", "name": "TTTM Vincom Xuân Khánh", "latitude": 10.024806699830012, "longitude": 105.77447502118535, "demand": 4},
        {"code": "LOC-09", "name": "Siêu thị GO! Cần Thơ", "latitude": 10.014561797291188, "longitude": 105.78301184160325, "demand": 5},
        {"code": "LOC-10", "name": "Chợ Cái Răng", "latitude": 10.005522748399304, "longitude": 105.75019017838079, "demand": 2},
        {"code": "LOC-11", "name": "ĐH Tây Đô", "latitude": 9.999018448807485, "longitude": 105.75960013819717, "demand": 3},
        {"code": "LOC-12", "name": "Công viên Lưu Hữu Phước", "latitude": 10.032203095147725, "longitude": 105.78201592959599, "demand": 2},
        {"code": "LOC-13", "name": "ĐH Kỹ thuật - Công nghệ Cần Thơ", "latitude": 10.046933040300678, "longitude": 105.76842982695476, "demand": 3},
        {"code": "LOC-14", "name": "Công viên Sông Hậu", "latitude": 10.049327970020423, "longitude": 105.79067783786995, "demand": 2},
        {"code": "LOC-15", "name": "Chân Cầu Quang Trung (Nguyễn Thị Minh Khai)", "latitude": 10.025705404991898, "longitude": 105.7807649354457, "demand": 1},
        {"code": "LOC-16", "name": "ĐH Nam Cần Thơ", "latitude": 10.005064478056019, "longitude":  105.72309532197355, "demand": 4},
        {"code": "LOC-17", "name": "KDC Nam Long 2 (Gần Coffee Trung Nguyên)", "latitude": 9.997076355234237, "longitude": 105.78209280981162, "demand": 2},
        {"code": "LOC-18", "name": "Đường số 1 KDC Metro", "latitude": 10.021833310319465, "longitude": 105.76092976334914, "demand": 5},
        {"code": "LOC-19", "name": "ĐH FPT", "latitude": 10.012532234871344, "longitude": 105.73256073003853, "demand": 3},
        {"code": "LOC-20", "name": "Nhà sách FAHASA", "latitude": 10.028442532650772, "longitude": 105.77883702198014, "demand": 6},
    ]
    client.table("locations").upsert(locations, on_conflict="code").execute()

    print(f"students={len(student_ids)} drivers={len(driver_ids)} "
          f"vehicles={len(vehicles)} locations={len(locations)}")

if __name__ == "__main__":
    main()