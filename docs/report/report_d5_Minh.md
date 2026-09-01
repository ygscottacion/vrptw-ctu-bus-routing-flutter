# Báo cáo T5 (Ngày 5) — Minh, DB/Supabase

**Trạng thái: Hoàn tất, đã pass toàn bộ bước.**

## Đã làm

- Migration `gps_logs` (bảng + constraint + index + RLS deny-all + retention 48h qua `pg_cron`) — merge OK, `alembic upgrade head` chạy sạch trên staging.
- Query plan (`EXPLAIN ANALYZE, BUFFERS`) cho 3 truy vấn: vị trí mới nhất theo route, lịch sử N phút gần nhất, và query xoá theo retention — đều dùng đúng index, không Seq Scan.
- Xác nhận job `gps_logs_retention_cleanup` trong `cron.job` đã đăng ký, `active = true`.

## ⚠️ Lưu ý quan trọng — tránh lặp lại conflict migration

Hôm nay phát sinh **2 head song song**: Nhã tạo `20260901_rls_alembic_version` và Minh tạo `20260901_add_locations_code` cùng lúc từ chung 1 điểm gốc (`20260831_rls_policies_v1`). Đã xử lý bằng 1 migration merge (`20260901_merge_heads`), không mất dữ liệu, nhưng để tránh lặp lại:

**Trước khi tạo migration mới, mọi người chạy:**
```bash
docker compose exec web alembic heads
```
Nếu thấy **nhiều hơn 1 head** → báo ngay trong group trước khi viết thêm migration, đừng tự `down_revision` vào head cũ.

**Head hiện tại sau khi merge:** `20260902_gps_logs_v1`
→ Migration tiếp theo của bất kỳ ai (Nhã/Duy) nên đặt `down_revision = "20260902_gps_logs_v1"`, trừ khi có thông báo head mới hơn.

## Việc tồn đọng / cần phối hợp tiếp

- Chờ Duy/Nhã xác nhận API GPS POST/GET dùng đúng schema `gps_logs` đã chốt (`route_id, latitude, longitude, heading, speed, accuracy, recorded_at`).

