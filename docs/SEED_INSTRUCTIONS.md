# Deliverable T4.1: Supabase Data Seed & Idempotency Evidence

**1. Thông tin tài khoản Test (Staging)**
- Passwords được lưu trữ và chia sẻ qua kênh Secret/1Password của nội bộ team (Không public tại đây).
- **5 Students:** `student1@test.example.com` -> `student5@test.example.com`
- **2 Drivers:** `driver1@test.example.com` -> `driver2@test.example.com`

**2. Hướng dẫn chạy Seed Script**
Thiết lập các biến môi trường trước khi chạy (sử dụng PowerShell):

```powershell
$env:SUPABASE_URL = "[https://szybskwlctbynbkqnllv.supabase.co](https://szybskwlctbynbkqnllv.supabase.co)"
$env:SUPABASE_SERVICE_ROLE_KEY = "<LẤY_TỪ_1PASSWORD>"
$env:SEED_TEST_PASSWORD = "<LẤY_TỪ_1PASSWORD>"

docker compose exec `
  -e SUPABASE_URL=$env:SUPABASE_URL `
  -e SUPABASE_SERVICE_ROLE_KEY=$env:SUPABASE_SERVICE_ROLE_KEY `
  -e SEED_TEST_PASSWORD=$env:SEED_TEST_PASSWORD `
  web python scripts/seed_supabase.py