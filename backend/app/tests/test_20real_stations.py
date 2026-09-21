"""
backend/app/tests/test_20real_stations.py

Ngày 6 (Newplan): Test 20 trạm thực tế Cần Thơ.
- Kiểm tra tọa độ (bounds Cần Thơ)
- Gọi Goong Distance Matrix thật cho 20x20
- Kiểm tra route factor (đường thật / đường chim bay) bất thường
- Kiểm tra ETA bất thường (tái dùng goong_metrics.validate_eta_anomaly)
- Kiểm tra điểm không khớp đường (snap-to-road) qua Goong Direction API
- Xuất report dạng bảng ra console + file CSV

Chạy:
    docker compose exec web python -m app.tests.test_20real_stations
"""
import csv
import sys
from typing import List, Dict, Optional

from app.services.student_routing.helpers.distance_matrix import (
    GoongDistanceMatrixProvider,
    haversine_distance,
)
from app.services.student_routing.helpers.goong_metrics import goong_metrics

# =========================================================================
# Dữ liệu 20 trạm thật (lấy thủ công từ Google Maps)
# =========================================================================

STATIONS: List[Dict] = [
    {"code": "LOC-01", "name": "ĐH Cần Thơ - Khu II (Depot chính)", "lat": 10.028200, "lng": 105.768200, "demand": 0},
    {"code": "LOC-02", "name": "Bến Ninh Kiều", "lat": 10.032213, "lng": 105.787976, "demand": 2},
    {"code": "LOC-03", "name": "Bến xe Trung tâm Cần Thơ", "lat": 10.005198, "lng": 105.772084, "demand": 6},
    {"code": "LOC-04", "name": "Hẻm 51 - Hồ Búng Xán", "lat": 10.024814, "lng": 105.767565, "demand": 2},
    {"code": "LOC-05", "name": "ĐH Y Dược Cần Thơ", "lat": 10.034498, "lng": 105.755812, "demand": 4},
    {"code": "LOC-06", "name": "Bệnh viện Đa khoa thành phố Cần Thơ", "lat": 10.030945, "lng": 105.781573, "demand": 3},
    {"code": "LOC-07", "name": "TTTM Lotte Mart Cần Thơ", "lat": 10.042212, "lng": 105.766568, "demand": 3},
    {"code": "LOC-08", "name": "TTTM Vincom Xuân Khánh", "lat": 10.024807, "lng": 105.774475, "demand": 4},
    {"code": "LOC-09", "name": "Siêu thị GO! Cần Thơ", "lat": 10.014562, "lng": 105.783012, "demand": 5},
    {"code": "LOC-10", "name": "Chợ Cái Răng", "lat": 10.005523, "lng": 105.750190, "demand": 2},
    {"code": "LOC-11", "name": "ĐH Tây Đô", "lat": 9.999018, "lng": 105.759600, "demand": 3},
    {"code": "LOC-12", "name": "Công viên Lưu Hữu Phước", "lat": 10.032203, "lng": 105.782016, "demand": 2},
    {"code": "LOC-13", "name": "ĐH Kỹ thuật - Công nghệ Cần Thơ", "lat": 10.046933, "lng": 105.768430, "demand": 3},
    {"code": "LOC-14", "name": "Công viên Sông Hậu", "lat": 10.049328, "lng": 105.790678, "demand": 2},
    {"code": "LOC-15", "name": "Chân Cầu Quang Trung (Nguyễn Thị Minh Khai)", "lat": 10.025705, "lng": 105.780765, "demand": 1},
    {"code": "LOC-16", "name": "ĐH Nam Cần Thơ", "lat": 10.005064, "lng": 105.723095, "demand": 4},
    {"code": "LOC-17", "name": "KDC Nam Long 2 (Gần Coffee Trung Nguyên)", "lat": 9.997076, "lng": 105.782093, "demand": 2},
    {"code": "LOC-18", "name": "Đường số 1 KDC Metro", "lat": 10.021833, "lng": 105.760930, "demand": 5},
    {"code": "LOC-19", "name": "ĐH FPT", "lat": 10.012532, "lng": 105.732561, "demand": 3},
    {"code": "LOC-20", "name": "Nhà sách FAHASA", "lat": 10.028443, "lng": 105.778837, "demand": 6},
]

# Bounds nới rộng cho vùng Cần Thơ + lân cận (Ninh Kiều, Cái Răng, Bình Thủy)
CAN_THO_BOUNDS = {
    "lat_min": 9.90, "lat_max": 10.10,
    "lng_min": 105.65, "lng_max": 105.85,
}

# Route factor (đường thật / đường chim bay) hợp lý cho đô thị
ROUTE_FACTOR_MIN = 1.0
ROUTE_FACTOR_MAX = 3.5

# Ngưỡng lệch snap-to-road coi là bất thường (km)
SNAP_OFFSET_THRESHOLD_KM = 0.1


# =========================================================================
# 1. Kiểm tra tọa độ (bounds)
# =========================================================================

def check_bounds(stations: List[Dict]) -> List[str]:
    issues = []
    for s in stations:
        if not (CAN_THO_BOUNDS["lat_min"] <= s["lat"] <= CAN_THO_BOUNDS["lat_max"]):
            issues.append(f"{s['code']} ({s['name']}): lat={s['lat']} nằm ngoài vùng Cần Thơ")
        if not (CAN_THO_BOUNDS["lng_min"] <= s["lng"] <= CAN_THO_BOUNDS["lng_max"]):
            issues.append(f"{s['code']} ({s['name']}): lng={s['lng']} nằm ngoài vùng Cần Thơ")
    return issues


# =========================================================================
# 2. Route factor bất thường
# =========================================================================

def check_route_factors(
    stations: List[Dict],
    distance_matrix: List[List[float]],
) -> List[Dict]:
    """Trả về danh sách cặp điểm có route factor bất thường."""
    issues = []
    n = len(stations)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            straight_km = haversine_distance(
                stations[i]["lat"], stations[i]["lng"],
                stations[j]["lat"], stations[j]["lng"],
            )
            route_km = distance_matrix[i][j]
            if straight_km <= 0.05:  # 2 điểm quá gần nhau, bỏ qua
                continue
            factor = route_km / straight_km
            if factor < ROUTE_FACTOR_MIN or factor > ROUTE_FACTOR_MAX:
                issues.append({
                    "from": stations[i]["code"],
                    "to": stations[j]["code"],
                    "straight_km": round(straight_km, 3),
                    "route_km": round(route_km, 3),
                    "factor": round(factor, 2),
                })
    return issues


# =========================================================================
# 3. ETA bất thường — tái dùng goong_metrics.validate_eta_anomaly
# =========================================================================

def check_eta_anomalies(
    stations: List[Dict],
    distance_matrix: List[List[float]],
    time_matrix: List[List[float]],
) -> List[str]:
    issues = []
    n = len(stations)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            summary = f"{stations[i]['code']}->{stations[j]['code']}"
            msg = goong_metrics.validate_eta_anomaly(
                distance_matrix[i][j], time_matrix[i][j], summary
            )
            if msg:
                issues.append(msg)
    return issues


# =========================================================================
# 4. Điểm không khớp đường (snap-to-road)
#    LƯU Ý: cần xem app/services/student_routing/helpers/goong_direction.py
#    để biết chính xác field response trả về (đang giả định cấu trúc phổ
#    biến của Goong Direction API — cần verify lại, có thể phải sửa key).
# =========================================================================

def check_snap_to_road(stations: List[Dict]) -> List[str]:
    """
    Gọi Goong Direction API từ mỗi điểm tới điểm kế tiếp gần nhất, so
    khoảng cách toạ độ gốc với điểm bắt đầu route mà Goong trả về.

    TODO: cần thay bằng lời gọi thật tới GoongDirectionProvider (chưa có
    interface cụ thể — gửi nội dung goong_direction.py để hoàn thiện hàm
    này chính xác thay vì bỏ qua).
    """
    issues = []
    try:
        from app.services.student_routing.helpers.goong_direction import (
            GoongDirectionProvider,
        )
    except ImportError:
        issues.append(
            "SKIP: chưa có GoongDirectionProvider hoặc import sai — "
            "cần bổ sung nội dung goong_direction.py để hoàn thiện check này."
        )
        return issues

    provider = GoongDirectionProvider()
    for i, station in enumerate(stations):
        # So với điểm kế tiếp trong danh sách làm điểm đích tạm để lấy route
        target = stations[(i + 1) % len(stations)]
        try:
            result = provider.get_direction(
                origin={"lat": station["lat"], "lng": station["lng"]},
                destination={"lat": target["lat"], "lng": target["lng"]},
            )
            # CẦN VERIFY: field thật trong response Goong Direction
            snapped = result.get("routes", [{}])[0].get("legs", [{}])[0].get("start_location")
            if snapped:
                offset_km = haversine_distance(
                    station["lat"], station["lng"], snapped["lat"], snapped["lng"]
                )
                if offset_km > SNAP_OFFSET_THRESHOLD_KM:
                    issues.append(
                        f"{station['code']} ({station['name']}): snap lệch {offset_km*1000:.0f}m"
                    )
        except Exception as e:
            issues.append(f"{station['code']}: lỗi khi gọi Direction API — {e}")
    return issues


# =========================================================================
# Main
# =========================================================================

def main():
    print(f"=== Test {len(STATIONS)} trạm thật Cần Thơ ===\n")

    # --- 1. Bounds check ---
    print("--- 1. Kiểm tra tọa độ (bounds) ---")
    bounds_issues = check_bounds(STATIONS)
    if bounds_issues:
        for issue in bounds_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ Toàn bộ 20 trạm nằm trong vùng Cần Thơ hợp lệ.")

    # --- 2. Gọi Goong Distance Matrix thật ---
    print("\n--- 2. Gọi Goong Distance Matrix (20x20) ---")
    provider = GoongDistanceMatrixProvider()
    points = [{"lat": s["lat"], "lng": s["lng"]} for s in STATIONS]
    distance_matrix, time_matrix, source = provider.get_matrix(points, "MORNING_1")
    print(f"  Nguồn dữ liệu trả về: {source}")
    if source != "GOONG":
        print("  ⚠️  CẢNH BÁO: không dùng được Goong thật, đang fallback Haversine — "
              "kết quả route factor/ETA phía dưới sẽ KHÔNG có ý nghĩa kiểm tra thật.")

    # --- 3. Route factor ---
    print("\n--- 3. Kiểm tra route factor bất thường ---")
    factor_issues = check_route_factors(STATIONS, distance_matrix)
    if factor_issues:
        for issue in factor_issues:
            print(f"  ⚠️  {issue['from']}->{issue['to']}: factor={issue['factor']} "
                  f"(chim bay {issue['straight_km']}km, đường thật {issue['route_km']}km)")
    else:
        print("  ✅ Không có cặp điểm nào route factor bất thường.")

    # --- 4. ETA anomaly ---
    print("\n--- 4. Kiểm tra ETA bất thường ---")
    eta_issues = check_eta_anomalies(STATIONS, distance_matrix, time_matrix)
    if eta_issues:
        for issue in eta_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ Không có ETA bất thường.")

    # --- 5. Snap-to-road ---
    print("\n--- 5. Kiểm tra điểm không khớp đường (snap-to-road) ---")
    snap_issues = check_snap_to_road(STATIONS)
    if snap_issues:
        for issue in snap_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ Không phát hiện lệch snap-to-road.")

    # --- Xuất CSV tổng hợp ---
    import os
    if os.path.exists("/app") and os.path.isdir("/app"):
        output_path = "/app/test_20_stations_report.csv"
    else:
        output_path = os.path.join(os.path.dirname(__file__), "test_20_stations_report.csv")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "detail"])
        for issue in bounds_issues:
            writer.writerow(["bounds", issue])
        for issue in factor_issues:
            writer.writerow(["route_factor", f"{issue['from']}->{issue['to']}: {issue['factor']}"])
        for issue in eta_issues:
            writer.writerow(["eta_anomaly", issue])
        for issue in snap_issues:
            writer.writerow(["snap_to_road", issue])
    print(f"\nĐã xuất report: {output_path}")

    total_issues = len(bounds_issues) + len(factor_issues) + len(eta_issues) + len(snap_issues)
    print(f"\n=== Tổng kết: {total_issues} vấn đề phát hiện trên {len(STATIONS)} trạm ===")
    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()