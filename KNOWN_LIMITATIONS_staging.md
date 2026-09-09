# Known Limitations — MyCTU BUS Staging v1.0

**Release Tag:** `staging-v1.0`  
**Commit:** `c49cc8d`  
**Ngày phát hành:** 2026-09-05  
**Môi trường:** Staging (Render + Supabase `szybskwlctbynbkqnllv`)

---

## Trạng thái nghiệm thu

| Hạng mục | Trạng thái | Evidence |
|---|---|---|
| E2E Vòng 2 (20/20 test cases) | ✅ ĐẠT | `docs/report/report_T7_Loi.md` |
| BUG-VRPTW-01 (route sinh "thành công giả") | ✅ ĐÃ FIX — 5/5 tests PASS | Xem mục 1 bên dưới |
| RLS A/B isolation (student A vs B) | ✅ ĐẠT | TC_SEC_01 → TC_SEC_04 |
| Role escalation privilege (critical fix T7) | ✅ ĐÃ VÁ | `20260904_fix_profiles_role_escalation.py` |
| Deadline 21:59/22:01 theo ICT | ✅ ĐẠT | TC_DL_01 → TC_DL_04 |
| QR check-in idempotency | ✅ ĐẠT | TC_QR_01 → TC_QR_03 |
| GPS foreground tracking | ✅ ĐẠT | TC_GPS_01 → TC_GPS_03 |

---

## 1. BUG-VRPTW-01 — Trạng thái: ĐÃ FIX ✅

**Mô tả lỗi gốc:** Route job báo `SUCCEEDED` nhưng `route_stops` rỗng/thiếu, do node key dạng `location_0` bị ép thẳng thành UUID thay vì tra cứu qua mapping.

**Fix đã thực hiện (5 phần):**
1. **Data Contract:** `VRPTWSolverService` chỉ trả node key kỹ thuật (`depot`, `location_0`, ...), không trả UUID trực tiếp.
2. **UUID Lookup:** `route_worker.py` tạo `uuid_lookup: dict[str, UUID]` bất biến, map từng node key sang UUID PostgreSQL thật.
3. **Post-validation:** Sau khi tạo route/stops, validate đủ 5 điều kiện trước khi set `SUCCEEDED`.
4. **Error Handling:** `UnmappedSolverNodeError` và `RouteStopValidationError` — không bỏ qua, luôn raise và log đầy đủ.
5. **Atomic Transaction:** Toàn bộ `CREATE route + stops + UPDATE tickets` trong một transaction; bất kỳ lỗi nào → rollback toàn bộ.

**Test suite kết quả (chạy ngày 2026-09-05):**
```
tests/test_bug_vrptw_01_fix.py::test_unit_uuid_mapping                           PASSED
tests/test_bug_vrptw_01_fix.py::test_unit_transaction_rollback_on_error          PASSED
tests/test_bug_vrptw_01_fix.py::test_e2e_bug_vrptw_01_scenario                  PASSED
tests/test_bug_vrptw_01_fix.py::test_regression_location_0_bug                   PASSED
tests/test_bug_vrptw_01_fix.py::test_generate_api_persists_complete_stop_manifest PASSED

======================== 5 passed in 0.80s ========================
```

**Kết luận:** BUG-VRPTW-01 đã fix xong, đã qua đủ regression test suite. **ĐỦ ĐIỀU KIỆN SIGN-OFF.**

---

## 2. Flutter APK — Fallback localhost (Known, Không phải P0)

**Mô tả:** `lib/config/api_config.dart` có fallback hardcode `localhost:8000` và `10.0.2.2:8000` khi `BASE_URL` không được truyền qua `--dart-define`.

**Tại sao không phải P0:** Code fallback chỉ chạy trong môi trường development local. Staging APK bắt buộc phải được build với:
```bash
flutter build apk --dart-define=BASE_URL=https://<render-url>/api/v1 \
                   --dart-define=SUPABASE_URL=https://szybskwlctbynbkqnllv.supabase.co \
                   --dart-define=SUPABASE_ANON_KEY=<anon-key>
```
**Kiểm tra:** Khánh có trách nhiệm xác nhận staging APK build không chứa localhost trong output binary trước khi phân phối.

---

## 3. GPS — Chỉ hỗ trợ Foreground (By Design)

**Mô tả:** GPS tracking chỉ hoạt động khi app Flutter đang ở foreground. Khi app bị minimize hoặc màn hình tắt, GPS sẽ dừng.

**Lý do:** Background GPS service nằm ngoài phạm vi MVP (xem `implementation_plan_1-2_weeks_revised.md`).

**Workaround cho staging:** Tài xế giữ app mở trong suốt ca chạy. Background tracking là tính năng của Sprint tiếp theo.

---

## 4. WebSocket Bus Location — Chưa có Auth

**Mô tả:** Endpoint `WS /ws/bus-locations` không yêu cầu xác thực JWT. Bất kỳ client nào cũng có thể connect và nhận broadcast vị trí.

**Đánh giá rủi ro:** Thấp trong môi trường staging (không có vị trí xe thật, chỉ dữ liệu test). Cần thêm auth trước khi production.

---

## 5. Wallet/Ledger — Dữ liệu Test, Không có Giao dịch Thật

**Mô tả:** Toàn bộ số dư ví và lịch sử giao dịch là dữ liệu seed test. Không có tích hợp payment gateway (MoMo/VNPay) trong MVP này.

---

## 6. Scheduler — Trigger Thủ Công cho Staging

**Mô tả:** Cron job sinh tuyến yêu cầu trigger thủ công hoặc Render Cron Job. Không có tự động schedule production. Cần cấu hình `X-Cron-Secret` đúng.

---

## 7. Giới hạn Hiệu năng Solver (Known Limits)

| Quy mô | Thời gian ước tính |
|---|---|
| 5 sinh viên, 2 xe | < 5s |
| 10 sinh viên, 2 xe | < 15s |
| 20 sinh viên, 2 xe | < 45s |

Trên 20 sinh viên/ca chưa được benchmark — nằm ngoài phạm vi MVP.

---

## 8. Test Suite — 13 Integration Tests Cần PostgreSQL Thật

**Mô tả:** 13 test trong `tests/api/test_supabase_auth.py`, `tests/test_crud.py`, `tests/test_leader_features.py` bị lỗi `SQLAlchemy OperationalError` khi chạy trên SQLite local.

**Nguyên nhân:** Các test này cần kết nối PostgreSQL/Supabase thật với schema `auth.users`.

**Không phải bug trong code:** Tất cả 53 unit test và integration test khác đều PASS. Các test này chỉ fail ở môi trường CI local không có PG — chúng pass khi chạy trên staging thật.

---

## Quyết định Sign-off

| Hạng mục | Quyết định |
|---|---|
| BUG-VRPTW-01 | ✅ SIGN-OFF — đã fix, đủ evidence |
| E2E Vòng 2 | ✅ SIGN-OFF — 20/20 PASS |
| RLS bảo mật | ✅ SIGN-OFF — pass A/B test, đã vá role escalation |
| **MVP Staging tổng thể** | ✅ **SIGN-OFF** — sẵn sàng release `staging-v1.0` |

**Người nghiệm thu cuối:** Nhã (Leader/Backend) + Lợi (QA Lead)  
**Ngày:** 2026-09-05
