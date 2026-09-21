import math
from typing import List, Dict, Any

class SweepClusteringService:
    """
    Giai đoạn 1: Thuật toán Sweep (Quét theo góc cực)
    - Nhận vào Depot (trạm xuất phát tâm), danh sách các điểm đón (Locations) và danh sách Xe buýt (Vehicles).
    - Tính góc cực (Polar Angle) của từng điểm đón so với Depot.
    - Sắp xếp các điểm đón theo góc cực tăng dần (0 đến 360 độ).
    - Gom cụm các điểm đón vào từng xe sao cho tổng nhu cầu (demand) <= sức chứa của xe (capacity).
    """

    @staticmethod
    def calculate_polar_angle(depot_lat: float, depot_lng: float, point_lat: float, point_lng: float) -> float:
        """Tính góc cực (tính bằng Radian/Độ) giữa điểm đón và Depot tâm"""
        d_lat = point_lat - depot_lat
        d_lng = point_lng - depot_lng
        angle = math.atan2(d_lat, d_lng)
        if angle < 0:
            angle += 2 * math.pi
        return angle

    @staticmethod
    def calculate_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Tính khoảng cách Haversine giữa 2 tọa độ (km)"""
        r = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lng = math.radians(lng2 - lng1)
        a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
        return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def estimate_route_duration(
        self,
        depot: Dict[str, Any],
        stops: List[Dict[str, Any]],
        average_speed_km_h: float = 30.0
    ) -> float:
        """
        Ước tính tổng thời gian hành trình toàn tuyến (phút) từ Depot -> các trạm -> Depot.
        """
        if not stops:
            return 0.0
        depot_lat = depot.get("latitude", depot.get("lat", 10.0302))
        depot_lng = depot.get("longitude", depot.get("lng", 105.7721))

        total_dist = 0.0
        curr_lat, curr_lng = depot_lat, depot_lng
        for s in stops:
            s_lat = s.get("latitude", s.get("lat", 0.0))
            s_lng = s.get("longitude", s.get("lng", 0.0))
            total_dist += self.calculate_distance_km(curr_lat, curr_lng, s_lat, s_lng)
            curr_lat, curr_lng = s_lat, s_lng

        # Quay về depot
        total_dist += self.calculate_distance_km(curr_lat, curr_lng, depot_lat, depot_lng)
        # Thời gian (phút) = (quãng đường / vận tốc) * 60 + thời gian dừng đón (1 phút/trạm)
        travel_time_min = (total_dist / average_speed_km_h) * 60.0
        dwell_time_min = len(stops) * 1.0
        return travel_time_min + dwell_time_min

    def cluster_locations(
        self,
        depot: Dict[str, Any],
        locations: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        max_route_duration_minutes: float = 90.0,
        max_passenger_capacity: int = 45,
        enforce_min_vehicles_for_60_students: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Input:
            depot: {"id": 0, "latitude": float, "longitude": float}
            locations: [{"id": 1, "latitude": float, "longitude": float, "demand": int, ...}]
            vehicles: [{"id": 1, "capacity": int, ...}]
            max_route_duration_minutes: Ngưỡng tối đa thời gian toàn tuyến (mặc định 90 phút theo chuẩn Khánh validation Ngày 9)
            max_passenger_capacity: Sức chứa tối đa chuẩn mỗi xe (mặc định 45 khách)
        Output:
            Danh sách cụm xe: [{"vehicle_id": 1, "capacity": 45, "current_demand": x, "stops": [loc1, ...]}, ...]
        """
        if not locations or not vehicles:
            return []

        # 1. Tính góc cực cho từng location
        depot_lat = depot.get("latitude", depot.get("lat", 10.0302))
        depot_lng = depot.get("longitude", depot.get("lng", 105.7721))

        total_demand = sum(loc.get("demand", loc.get("pickup_student_count", 1)) for loc in locations)

        locations_with_angle = []
        for loc in locations:
            l_lat = loc.get("latitude", loc.get("lat", 0.0))
            l_lng = loc.get("longitude", loc.get("lng", 0.0))
            angle = self.calculate_polar_angle(depot_lat, depot_lng, l_lat, l_lng)
            loc_copy = dict(loc)
            loc_copy["polar_angle"] = angle
            locations_with_angle.append(loc_copy)

        # 2. Sắp xếp các điểm đón theo góc cực tăng dần
        sorted_locations = sorted(locations_with_angle, key=lambda x: x["polar_angle"])

        # 3. Phân bổ và gom cụm
        # Nếu có >= 60 sinh viên và có >= 2 xe, đảm bảo mỗi xe không chứa quá 45 sinh viên
        # và phân bổ chia đều để dùng >= 2 xe
        effective_vehicles = [dict(v) for v in vehicles]
        if enforce_min_vehicles_for_60_students and total_demand >= 60 and len(effective_vehicles) >= 2:
            # Điều chỉnh capacity trần cho xe không vượt quá 45 hoặc phân bổ tải hợp lý
            for v in effective_vehicles:
                v["capacity"] = min(v.get("capacity", max_passenger_capacity), max_passenger_capacity)

        clusters = []
        vehicle_index = 0
        current_vehicle = effective_vehicles[vehicle_index]
        effective_capacity = min(current_vehicle.get("capacity", max_passenger_capacity), max_passenger_capacity)

        current_cluster = {
            "vehicle_id": current_vehicle["id"],
            "capacity": effective_capacity,
            "current_demand": 0,
            "stops": []
        }

        for loc in sorted_locations:
            loc_demand = loc.get("demand", loc.get("pickup_student_count", 1))
            if loc_demand <= 0:
                loc_demand = 1

            # Kiểm tra:
            # 1. Quá tải (Capacity constraint)
            would_overload = (current_cluster["current_demand"] + loc_demand > current_cluster["capacity"])

            # 2. Quá giờ (Duration constraint)
            candidate_stops = current_cluster["stops"] + [loc]
            est_duration = self.estimate_route_duration(depot, candidate_stops)
            would_overtime = (est_duration > max_route_duration_minutes) and (len(current_cluster["stops"]) > 0)

            # Nếu vi phạm quá tải HOẶC quá giờ -> Chuyển sang xe tiếp theo
            if would_overload or would_overtime:
                if current_cluster["stops"]:
                    clusters.append(current_cluster)
                    vehicle_index += 1

                if vehicle_index < len(effective_vehicles):
                    current_vehicle = effective_vehicles[vehicle_index]
                    effective_capacity = min(current_vehicle.get("capacity", max_passenger_capacity), max_passenger_capacity)
                    current_cluster = {
                        "vehicle_id": current_vehicle["id"],
                        "capacity": effective_capacity,
                        "current_demand": 0,
                        "stops": []
                    }
                else:
                    # Nếu hết danh sách xe cấu hình sẵn:
                    # Tuyệt đối KHÔNG nhồi nhét gây quá tải vào xe cuối!
                    # Tự động kích hoạt xe dự phòng (Standby Vehicle) với sức chứa chuẩn
                    standby_id = f"BUS-STANDBY-{vehicle_index + 1}"
                    current_cluster = {
                        "vehicle_id": standby_id,
                        "capacity": max_passenger_capacity,
                        "current_demand": 0,
                        "stops": []
                    }

            current_cluster["stops"].append(loc)
            current_cluster["current_demand"] += loc_demand

        if current_cluster["stops"] and current_cluster not in clusters:
            clusters.append(current_cluster)

        # Đảm bảo nếu total_demand >= 60 và len(effective_vehicles) >= 2 thì kết quả phải có >= 2 cụm xe
        if total_demand >= 60 and len(clusters) < 2 and len(effective_vehicles) >= 2:
            # Tách cụm hiện tại thành 2 cụm nếu lỡ bị dồn vào 1 cụm
            single_cluster = clusters[0]
            mid_idx = len(single_cluster["stops"]) // 2
            cluster1_stops = single_cluster["stops"][:mid_idx]
            cluster2_stops = single_cluster["stops"][mid_idx:]

            c1 = {
                "vehicle_id": effective_vehicles[0]["id"],
                "capacity": min(effective_vehicles[0].get("capacity", max_passenger_capacity), max_passenger_capacity),
                "current_demand": sum(s.get("demand", s.get("pickup_student_count", 1)) for s in cluster1_stops),
                "stops": cluster1_stops
            }
            c2 = {
                "vehicle_id": effective_vehicles[1]["id"],
                "capacity": min(effective_vehicles[1].get("capacity", max_passenger_capacity), max_passenger_capacity),
                "current_demand": sum(s.get("demand", s.get("pickup_student_count", 1)) for s in cluster2_stops),
                "stops": cluster2_stops
            }
            clusters = [c1, c2]

        return clusters
