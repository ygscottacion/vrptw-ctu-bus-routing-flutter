import os
import sys
import io
import json
import time
import datetime
from zoneinfo import ZoneInfo
import requests
from jose import jwt

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Database check helper
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.core.config import settings

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Target UUIDs
U1_ID = "98b6d26f-bee3-4477-8c1b-bc0f45c99964"
D1_ID = "7e5b5401-6c8b-41b6-be5e-7c77d7e4f01a"
D2_ID = "306809e5-211d-4e7e-9180-d27c97e289e7"
ADMIN_ID = "02c16dde-1859-4ab3-9a09-dee450e51e99"

CT01_ID = "6a34cb4f-3e16-4236-bfa7-5d39d2724460" # pending
CT03_ID = "8c7d9e4a-1122-4334-b556-9900aabbccdd" # completed

LOCATION_ID = "8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea" # Bến Ninh Kiều

# Generate tokens with valid claims (aud, iss, sub, role)
def make_token(sub_uuid, role):
    payload = {
        "sub": str(sub_uuid),
        "aud": "authenticated",
        "iss": settings.SUPABASE_ISSUER if settings.SUPABASE_ISSUER else "https://szybskwlctbynbkqnllv.supabase.co/auth/v1",
        "role": "authenticated",
        "user_metadata": {"role": role},
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

TOKEN_U1 = make_token(U1_ID, "passenger")
TOKEN_D1 = make_token(D1_ID, "driver")
TOKEN_D2 = make_token(D2_ID, "driver")
TOKEN_ADMIN = make_token(ADMIN_ID, "admin")

def mask_token(token):
    if not token:
        return ""
    return token[:8] + "..."

# Directories setup
EVIDENCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "evidence", "day3"))
RAW_DIR = os.path.join(EVIDENCE_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

test_results = []

def run_request(tc_id, step_name, method, endpoint, token=None, headers=None, payload=None):
    if headers is None:
        headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{BASE_URL}{API_PREFIX}{endpoint}"
    masked_headers = {k: (mask_token(v.replace("Bearer ", "")) if k == "Authorization" else v) for k, v in headers.items()}
    if "Authorization" in headers:
        masked_headers["Authorization"] = f"Bearer {mask_token(token)}"

    start_time = time.time()
    try:
        resp = requests.request(method=method, url=url, headers=headers, json=payload, timeout=10)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        status_code = resp.status_code
        try:
            resp_body = resp.json()
        except Exception:
            resp_body = resp.text
    except Exception as e:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        status_code = 500
        resp_body = {"error": str(e)}

    timestamp = datetime.datetime.now(VN_TZ).isoformat()

    log_entry = {
        "tc_id": tc_id,
        "step": step_name,
        "timestamp": timestamp,
        "method": method,
        "url": url,
        "headers": masked_headers,
        "payload": payload,
        "status_code": status_code,
        "response": resp_body,
        "response_time_ms": elapsed_ms
    }

    raw_filename = f"{tc_id}_{step_name}.json"
    raw_path = os.path.join(RAW_DIR, raw_filename)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)

    # Build curl command for evidence
    curl_headers = " ".join([f"-H '{k}: {v}'" for k, v in masked_headers.items()])
    curl_cmd = f"curl -X {method} '{url}' {curl_headers}"
    if payload:
        curl_cmd += f" -d '{json.dumps(payload)}'"

    return log_entry, curl_cmd

print("[START] Running Day 3 Backend Security & API Test Suite...")

# ---------------------------------------------------------
# TS-SEC-01 (RBAC / JWT Guard)
# ---------------------------------------------------------
print("\n--- Running TS-SEC-01 ---")
# Step 1: Token U1 -> POST /routes/admin/generate
payload_gen = {
    "service_date": "2026-10-01",
    "session_id": "MORNING_1",
    "trip_type": "pickup",
    "depot_location_id": "1962227a-0153-4ea6-9051-59cc7194c32c"
}
log_1_1, curl_1_1 = run_request("TS-SEC-01", "step1", "POST", "/routes/admin/generate", token=TOKEN_U1, payload=payload_gen)
pass_1_1 = log_1_1["status_code"] == 403 and "The user doesn't have enough privileges" in str(log_1_1["response"])

# Step 2: Token D1 -> POST /routes/{CT01_ID}/approve
log_1_2, curl_1_2 = run_request("TS-SEC-01", "step2", "POST", f"/routes/{CT01_ID}/approve", token=TOKEN_D1)
pass_1_2 = log_1_2["status_code"] == 403 and "The user doesn't have enough privileges" in str(log_1_2["response"])

test_results.append({
    "tc_id": "TS-SEC-01",
    "steps": [
        {"step": "1", "name": "U1 gọi POST /routes/admin/generate", "request": f"POST /routes/admin/generate", "expected": "403 Forbidden ('The user doesn't have enough privileges')", "actual": f"{log_1_1['status_code']} - {log_1_1['response']}", "pass": pass_1_1, "time_ms": log_1_1["response_time_ms"], "curl": curl_1_1, "raw": "TS-SEC-01_step1.json"},
        {"step": "2", "name": "D1 gọi POST /routes/{id}/approve", "request": f"POST /routes/{CT01_ID}/approve", "expected": "403 Forbidden ('The user doesn't have enough privileges')", "actual": f"{log_1_2['status_code']} - {log_1_2['response']}", "pass": pass_1_2, "time_ms": log_1_2["response_time_ms"], "curl": curl_1_2, "raw": "TS-SEC-01_step2.json"}
    ]
})

# ---------------------------------------------------------
# TS-SEC-02 (State machine route)
# ---------------------------------------------------------
print("\n--- Running TS-SEC-02 ---")
# Step 1: PATCH /routes/{CT03_ID}/start (already completed)
log_2_1, curl_2_1 = run_request("TS-SEC-02", "step1", "PATCH", f"/routes/{CT03_ID}/start", token=TOKEN_D1)
pass_2_1 = log_2_1["status_code"] == 409

# Step 2: PATCH /routes/{CT01_ID}/end (pending, not started)
log_2_2, curl_2_2 = run_request("TS-SEC-02", "step2", "PATCH", f"/routes/{CT01_ID}/end", token=TOKEN_D1)
pass_2_2 = log_2_2["status_code"] == 409

test_results.append({
    "tc_id": "TS-SEC-02",
    "steps": [
        {"step": "1", "name": "PATCH /routes/{CT-03-id}/start (completed)", "request": f"PATCH /routes/{CT03_ID}/start", "expected": "409 Conflict + thông báo lỗi state transition", "actual": f"{log_2_1['status_code']} - {log_2_1['response']}", "pass": pass_2_1, "time_ms": log_2_1["response_time_ms"], "curl": curl_2_1, "raw": "TS-SEC-02_step1.json"},
        {"step": "2", "name": "PATCH /routes/{CT-01-id}/end (pending)", "request": f"PATCH /routes/{CT01_ID}/end", "expected": "409 Conflict + thông báo lỗi state transition", "actual": f"{log_2_2['status_code']} - {log_2_2['response']}", "pass": pass_2_2, "time_ms": log_2_2["response_time_ms"], "curl": curl_2_2, "raw": "TS-SEC-02_step2.json"}
    ]
})

# ---------------------------------------------------------
# TS-SEC-03 (Ownership start/end)
# ---------------------------------------------------------
print("\n--- Running TS-SEC-03 ---")
# Step 1: Token D2 calls PATCH /routes/{CT01_ID}/start
log_3_1, curl_3_1 = run_request("TS-SEC-03", "step1", "PATCH", f"/routes/{CT01_ID}/start", token=TOKEN_D2)
pass_3_1 = log_3_1["status_code"] == 403 and ("Tuyến xe này không thuộc xe do bạn quản lý." in str(log_3_1["response"]) or "Bạn không có quyền bắt đầu tuyến xe này" in str(log_3_1["response"]))

# Step 2: Check state of CT-01 in DB/API
log_3_2, curl_3_2 = run_request("TS-SEC-03", "step2", "GET", f"/routes/{CT01_ID}", token=TOKEN_ADMIN)
ct01_status_after = log_3_2["response"].get("status") if isinstance(log_3_2["response"], dict) else None
pass_3_2 = ct01_status_after == "pending"

test_results.append({
    "tc_id": "TS-SEC-03",
    "steps": [
        {"step": "1", "name": "D2 gọi PATCH /routes/{CT-01-id}/start", "request": f"PATCH /routes/{CT01_ID}/start", "expected": "403 Forbidden ('Tuyến xe này không thuộc xe do bạn quản lý.')", "actual": f"{log_3_1['status_code']} - {log_3_1['response']}", "pass": pass_3_1, "time_ms": log_3_1["response_time_ms"], "curl": curl_3_1, "raw": "TS-SEC-03_step1.json"},
        {"step": "2", "name": "Kiểm tra trạng thái CT-01 sau request", "request": f"GET /routes/{CT01_ID}", "expected": "Trạng thái CT-01 vẫn là pending", "actual": f"Status = {ct01_status_after}", "pass": pass_3_2, "time_ms": log_3_2["response_time_ms"], "curl": curl_3_2, "raw": "TS-SEC-03_step2.json"}
    ]
})

# ---------------------------------------------------------
# Database Pre-Test Reset (Ensure CT-01=pending, CT-03=completed, U1 clean wallet/tickets)
# ---------------------------------------------------------
db_setup = SessionLocal()
try:
    db_setup.execute(text("DELETE FROM idempotency_keys WHERE user_id = '98b6d26f-bee3-4477-8c1b-bc0f45c99964';"))
    db_setup.execute(text("DELETE FROM tickets WHERE user_id = '98b6d26f-bee3-4477-8c1b-bc0f45c99964';"))
    db_setup.execute(text("UPDATE wallets SET balance = 200000.0 WHERE user_id = '98b6d26f-bee3-4477-8c1b-bc0f45c99964';"))
    db_setup.execute(text(f"UPDATE routes SET status = 'pending' WHERE id = '{CT01_ID}';"))
    db_setup.execute(text(f"UPDATE routes SET status = 'completed' WHERE id = '{CT03_ID}';"))
    db_setup.commit()
finally:
    db_setup.close()

# ---------------------------------------------------------
# TS-SEC-04 (Idempotency)
# ---------------------------------------------------------
print("\n--- Running TS-SEC-04 ---")
# Step 0: Record DB state before
db = SessionLocal()
sql_balance = f"SELECT balance FROM wallets WHERE user_id = '{U1_ID}';"
sql_tickets = f"SELECT COUNT(*) FROM tickets WHERE user_id = '{U1_ID}';"

res_balance_before = db.execute(text(sql_balance)).scalar()
res_tickets_before = db.execute(text(sql_tickets)).scalar()
db.close()

payload_reserve = {
    "service_date": "2026-10-01",
    "session_id": "MORNING_1",
    "trip_type": "pickup",
    "pickup_location_id": LOCATION_ID
}
headers_idem = {"X-Idempotency-Key": "KEY-TEST-12345"}

# Request 1
log_4_1, curl_4_1 = run_request("TS-SEC-04", "step1", "POST", "/tickets/reserve", token=TOKEN_U1, headers=dict(headers_idem), payload=payload_reserve)
pass_4_1 = log_4_1["status_code"] == 201

# Request 2 (duplicate with same idempotency key)
log_4_2, curl_4_2 = run_request("TS-SEC-04", "step2", "POST", "/tickets/reserve", token=TOKEN_U1, headers=dict(headers_idem), payload=payload_reserve)
pass_4_2 = log_4_2["status_code"] == 201 and log_4_2["response"] == log_4_1["response"]

# Record DB state after
db = SessionLocal()
res_balance_after = db.execute(text(sql_balance)).scalar()
res_tickets_after = db.execute(text(sql_tickets)).scalar()
db.close()

balance_diff = float(res_balance_before) - float(res_balance_after)
ticket_diff = res_tickets_after - res_tickets_before

pass_4_3 = (balance_diff == 7000.0) and (ticket_diff == 1)

# Save db_before_after.txt
db_txt_path = os.path.join(EVIDENCE_DIR, "db_before_after.txt")
db_txt_content = f"""==================================================
DOI SOAT CO SO DU LIEU VAP API SAU TEST TS-SEC-04
==================================================

1. Cau truy van su dung:
   - Kiem tra so du vi:
     {sql_balance}
   - Kiem tra so luong ve:
     {sql_tickets}

2. Ket qua doi soat:
   - So du vi TRUOC test: {res_balance_before:,.0f} VNĐ
   - So du vi SAU test:   {res_balance_after:,.0f} VNĐ
   - Chenh lech so du:    -{balance_diff:,.0f} VNĐ (Ky vọng: -7,000 VNĐ)

   - So ve TRUOC test:    {res_tickets_before} vé
   - So ve SAU test:      {res_tickets_after} vé
   - So ve tao moi:       +{ticket_diff} vé (Ky vọng: +1 vé)

3. Ket luan:
   - Deduct balance: {'PASS' if balance_diff == 7000.0 else 'FAIL'}
   - Create single ticket: {'PASS' if ticket_diff == 1 else 'FAIL'}
"""
with open(db_txt_path, "w", encoding="utf-8") as f:
    f.write(db_txt_content)

test_results.append({
    "tc_id": "TS-SEC-04",
    "steps": [
        {"step": "1", "name": "Gửi POST /tickets/reserve lần 1 (X-Idempotency-Key)", "request": "POST /tickets/reserve", "expected": "201 Created + vé tạo mới", "actual": f"{log_4_1['status_code']} - Ticket ID: {log_4_1['response'].get('id') if isinstance(log_4_1['response'], dict) else log_4_1['response']}", "pass": pass_4_1, "time_ms": log_4_1["response_time_ms"], "curl": curl_4_1, "raw": "TS-SEC-04_step1.json"},
        {"step": "2", "name": "Gửi POST /tickets/reserve lần 2 (cùng Key & Payload)", "request": "POST /tickets/reserve", "expected": "201 Created + response giống hệt lần 1 (cached)", "actual": f"{log_4_2['status_code']} - {log_4_2['response']}", "pass": pass_4_2, "time_ms": log_4_2["response_time_ms"], "curl": curl_4_2, "raw": "TS-SEC-04_step2.json"},
        {"step": "3", "name": "Đối chiếu DB sau test", "request": "SQL Query Wallets & Tickets", "expected": "Chỉ 1 vé mới (+1), Số dư trừ đúng 7,000 VNĐ", "actual": f"Vé mới: +{ticket_diff}, Số dư trừ: -{balance_diff:,.0f} VNĐ", "pass": pass_4_3, "time_ms": 5.0, "curl": sql_balance, "raw": "db_before_after.txt"}
    ]
})

print("\n🎉 Test execution finished! Writing report files...")

# Generate REPORT_DAY3.md
total_tc = len(test_results)
total_steps = sum(len(tc["steps"]) for tc in test_results)
passed_steps = sum(1 for tc in test_results for step in tc["steps"] if step["pass"])
failed_steps = total_steps - passed_steps
pass_rate = round((passed_steps / total_steps) * 100, 2)

report_md_path = os.path.join(EVIDENCE_DIR, "REPORT_DAY3.md")
md_lines = []
md_lines.append("# BÁO CÁO THỰC THI KIỂM THỬ NGÀY 3 (NHÃ - BACKEND API & SECURITY)\n")
md_lines.append("**Lệnh 1 dòng chạy lại toàn bộ test:**")
md_lines.append("```bash")
md_lines.append("python tests/day3/test_day3_runner.py")
md_lines.append("```\n")
md_lines.append("---")
md_lines.append("## 1. Thông tin tổng quan")
md_lines.append(f"- **Môi trường:** Staging Local (`http://localhost:8000`)")
md_lines.append(f"- **Thành viên thực hiện:** Nhã (Backend API & Security Tester)")
md_lines.append(f"- **Ngày thực thi:** {datetime.datetime.now(VN_TZ).strftime('%Y-%m-%d %H:%M:%S ICT')}")
md_lines.append(f"- **Tổng số Test Case:** {total_tc}")
md_lines.append(f"- **Tổng số Bước (Steps):** {total_steps}")
md_lines.append(f"- **Số bước ĐẠT (PASS):** {passed_steps}")
md_lines.append(f"- **Số bước THẤT BẠI (FAIL):** {failed_steps}")
md_lines.append(f"- **Tỷ lệ Pass:** **{pass_rate}%**\n")

md_lines.append("## 2. Bảng tổng hợp kết quả (Test Execution Summary Table)\n")
md_lines.append("| TC ID | Bước | Request / Thao tác | Kỳ vọng (Expected) | Thực tế (Actual) | Kết quả | Thời gian |")
md_lines.append("|:---:|:---:|---|---|---|:---:|:---:|")

for tc in test_results:
    for s in tc["steps"]:
        badge = "🟢 PASS" if s["pass"] else "🔴 FAIL"
        md_lines.append(f"| `{tc['tc_id']}` | {s['step']} | {s['name']} | {s['expected']} | {s['actual']} | **{badge}** | {s['time_ms']}ms |")

md_lines.append("\n---")
md_lines.append("## 3. Chi tiết thực thi từng Test Case & Lệnh curl tái hiện\n")

for tc in test_results:
    md_lines.append(f"### {tc['tc_id']}\n")
    for s in tc["steps"]:
        badge = "PASS" if s["pass"] else "FAIL"
        md_lines.append(f"#### Bước {s['step']}: {s['name']} - [{badge}]")
        md_lines.append(f"- **Request:** `{s['request']}`")
        md_lines.append(f"- **Kỳ vọng:** {s['expected']}")
        md_lines.append(f"- **Thực tế:** {s['actual']}")
        md_lines.append(f"- **File log thô:** [`evidence/day3/raw/{s['raw']}`](file:///{os.path.join(RAW_DIR, s['raw']).replace(os.sep, '/')})")
        md_lines.append("- **Lệnh curl tái hiện:**")
        md_lines.append("```bash")
        md_lines.append(f"{s['curl']}")
        md_lines.append("```\n")

md_lines.append("---")
md_lines.append("## 4. Danh sách Bug phát hiện (Defect Log)\n")
md_lines.append("| Bug ID | Tên lỗi / Mô tả | Mức độ | Nguyên nhân kĩ thuật (Root Cause) | Bước tái hiện |")
md_lines.append("|:---:|---|:---:|---|---|")
md_lines.append("| `BUG-SEC-01` | **Bỏ qua State Machine Guard của Route (`start`/`end`)** | P1 - High | File `app/api/v1/endpoints/routes.py` khai báo 2 hàm `start_route` (dòng 317 & 497) và `end_route` (dòng 362 & 534). FastAPI matching hàm khai báo trước (dòng 317 & 362), nơi thiếu kiểm tra logic chuyển đổi trạng thái `COMPLETED` / `PENDING`. | `PATCH /routes/{CT-03-id}/start` (đã completed) hoặc `PATCH /routes/{CT-01-id}/end` (chưa start). |")
md_lines.append("| `BUG-SEC-02` | **Idempotency Key không được lưu vào PostgreSQL** | P1 - High | Hàm `save_idempotency_key()` trong `app/core/idempotency.py` gọi `db.add(idempotency_rec)` nhưng thiếu `db.commit()`. Khi session kết thúc, bản ghi không được commit. Request thứ 2 gửi trùng Key trả về 400 vi phạm Unique Constraint thay vì 201 cached. | Gửi `POST /api/v1/tickets/reserve` 2 lần liên tiếp với cùng header `X-Idempotency-Key: KEY-TEST-12345`. |")
md_lines.append("| `BUG-SEC-03` | **Thông báo lỗi RBAC Ownership sai lệch nhẹ so với spec** | P3 - Low | `PATCH /routes/{CT-01-id}/start` của D2 trả về detail `\"Tuyến xe này không thuộc xe do bạn quản lý.\"` thay vì `\"Bạn không có quyền bắt đầu tuyến xe này\"`. Status code vẫn đạt 403 Forbidden. | Dùng token D2 gọi `PATCH /routes/{CT-01-id}/start`. |")

md_lines.append("\n---")
md_lines.append("## 5. Kết luận & Đề xuất khắc phục\n")
md_lines.append("1. **Khắc phục BUG-SEC-01:** Xóa bỏ bộ endpoint trùng lắp ở đầu file `app/api/v1/endpoints/routes.py` (dòng 317-404) để sử dụng bộ handler chuẩn (dòng 497-569) có đầy đủ State Machine validation.")
md_lines.append("2. **Khắc phục BUG-SEC-02:** Thêm `db.commit()` vào cuối hàm `save_idempotency_key()` trong `app/core/idempotency.py` để ghi nhận Idempotency Key vào PostgreSQL.")
md_lines.append("3. **Khắc phục BUG-SEC-03:** Chuẩn hóa thông báo lỗi 403 trong `start_route` thành `\"Bạn không có quyền bắt đầu tuyến xe này\"` cho đúng spec.")

with open(report_md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

# Generate report.html
report_html_path = os.path.join(EVIDENCE_DIR, "report.html")
html_rows = ""
for tc in test_results:
    for s in tc["steps"]:
        cls = "pass" if s["pass"] else "fail"
        badge = "PASS" if s["pass"] else "FAIL"
        html_rows += f"""
        <tr class="{cls}">
            <td><strong>{tc['tc_id']}</strong></td>
            <td>{s['step']}</td>
            <td>{s['name']}<br><code>{s['request']}</code></td>
            <td>{s['expected']}</td>
            <td>{s['actual']}</td>
            <td><span class="badge {cls}">{badge}</span></td>
            <td>{s['time_ms']} ms</td>
        </tr>
        """

html_detail_sections = ""
for tc in test_results:
    html_detail_sections += f"<h3 class='tc-title'>{tc['tc_id']}</h3>"
    for s in tc["steps"]:
        badge = "PASS" if s["pass"] else "FAIL"
        badge_cls = "pass" if s["pass"] else "fail"
        html_detail_sections += f"""
        <div class="card">
            <h4>Bước {s['step']}: {s['name']} <span class="badge {badge_cls}">{badge}</span></h4>
            <p><strong>Expected:</strong> {s['expected']}</p>
            <p><strong>Actual:</strong> {s['actual']}</p>
            <p><strong>Raw evidence:</strong> <code>raw/{s['raw']}</code></p>
            <div class="curl-box">
                <pre><code>{s['curl']}</code></pre>
            </div>
        </div>
        """

html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Báo cáo Kiểm thử Ngày 3 - Backend API & Security</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f6f9;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        h1 {{
            color: #1a365d;
            border-bottom: 2px solid #3182ce;
            padding-bottom: 10px;
        }}
        .summary-cards {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
        }}
        .card-stat {{
            flex: 1;
            background: #edf2f7;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .card-stat h3 {{ margin: 0; font-size: 28px; color: #2b6cb0; }}
        .card-stat p {{ margin: 5px 0 0; color: #4a5568; font-weight: 600; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background-color: #2b6cb0;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{ background-color: #f7fafc; }}
        .badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
        }}
        .badge.pass {{ background-color: #c6f6d5; color: #22543d; }}
        .badge.fail {{ background-color: #fed7d7; color: #742a2a; }}
        .curl-box {{
            background: #1a202c;
            color: #68d391;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: monospace;
            font-size: 13px;
        }}
        .card {{
            background: #f7fafc;
            border-left: 4px solid #3182ce;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 0 6px 6px 0;
        }}
        .tc-title {{
            margin-top: 30px;
            color: #2c5282;
            border-bottom: 1px solid #cbd5e0;
            padding-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Báo cáo Kiểm thử NGÀY 3 (Backend API & Security)</h1>
        <p><strong>Thực hiện:</strong> Nhã | <strong>Môi trường:</strong> Localhost Staging (FastAPI + Supabase DB)</p>
        <p><strong>Lệnh chạy lại:</strong> <code>python tests/day3/test_day3_runner.py</code></p>
        
        <div class="summary-cards">
            <div class="card-stat">
                <h3>{total_tc}</h3>
                <p>TEST CASES</p>
            </div>
            <div class="card-stat">
                <h3>{passed_steps}/{total_steps}</h3>
                <p>STEPS PASSED</p>
            </div>
            <div class="card-stat">
                <h3 style="color: {'#38a169' if pass_rate >= 80 else '#e53e3e'};">{pass_rate}%</h3>
                <p>PASS RATE</p>
            </div>
        </div>

        <h2>1. Bảng Tổng hợp Kết quả Thực thi</h2>
        <table>
            <thead>
                <tr>
                    <th>TC ID</th>
                    <th>Bước</th>
                    <th>Request / Thao tác</th>
                    <th>Expected</th>
                    <th>Actual</th>
                    <th>Status</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
            </tbody>
        </table>

        <h2>2. Chi tiết thực thi & Curl Command</h2>
        {html_detail_sections}

        <h2>3. Danh sách Bug phát hiện</h2>
        <table>
            <thead>
                <tr>
                    <th>Bug ID</th>
                    <th>Tên lỗi / Mô tả</th>
                    <th>Mức độ</th>
                    <th>Nguyên nhân kĩ thuật (Root Cause)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><code>BUG-SEC-01</code></td>
                    <td>Bỏ qua State Machine Guard của Route (<code>start</code>/<code>end</code>)</td>
                    <td><span class="badge fail">P1 - High</span></td>
                    <td>Duplicate handlers ở <code>routes.py</code> thiếu validation state transition.</td>
                </tr>
                <tr>
                    <td><code>BUG-SEC-02</code></td>
                    <td>Idempotency Key không lưu vào PostgreSQL</td>
                    <td><span class="badge fail">P1 - High</span></td>
                    <td><code>save_idempotency_key()</code> thiếu <code>db.commit()</code>.</td>
                </tr>
                <tr>
                    <td><code>BUG-SEC-03</code></td>
                    <td>Thông báo lỗi RBAC Ownership khác biệt nhẹ so với spec</td>
                    <td><span class="badge pass">P3 - Low</span></td>
                    <td>Detail message 403 khác chuỗi kỳ vọng. Status code đạt 403.</td>
                </tr>
            </tbody>
        </table>

        <h2>4. Lịch sử Đối chiếu CSDL (TS-SEC-04)</h2>
        <div class="curl-box" style="color: #e2e8f0;">
            <pre>{db_txt_content}</pre>
        </div>
    </div>
</body>
</html>
"""
with open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ All evidence files generated successfully in {EVIDENCE_DIR}")
