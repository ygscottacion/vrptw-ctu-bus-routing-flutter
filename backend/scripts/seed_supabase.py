"""
backend/scripts/seed_supabase.py
Chạy: SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python -m scripts.seed_supabase
KHÔNG commit service-role key vào repo. Đọc từ biến môi trường / secret manager.
"""
import os
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

STUDENTS = [f"student{i}@test.example.com" for i in range(1, 6)]   # 5 student
DRIVERS  = [f"driver{i}@test.example.com" for i in range(1, 3)]    # 2 driver
TEST_PASSWORD = os.environ["SEED_TEST_PASSWORD"]  # không hardcode

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
        {"code": "LOC-01", "name": "Khu II - ĐHCT", "latitude": 10.0299, "longitude": 105.7706},
        {"code": "LOC-02", "name": "Khu I - ĐHCT", "latitude": 10.0333, "longitude": 105.7833},
        {"code": "LOC-03", "name": "Ký túc xá", "latitude": 10.0250, "longitude": 105.7750},
        {"code": "LOC-04", "name": "Bến xe Cần Thơ", "latitude": 10.0000, "longitude": 105.7500},
        {"code": "LOC-05", "name": "Viện CNTT", "latitude": 10.0305, "longitude": 105.7711},
    ]
    client.table("locations").upsert(locations, on_conflict="code").execute()

    print(f"students={len(student_ids)} drivers={len(driver_ids)} "
          f"vehicles={len(vehicles)} locations={len(locations)}")

if __name__ == "__main__":
    main()