import math
from typing import List, Dict, Any
from app.services.student_routing import config


class SweepClusterer:
    """
    Thuật toán Sweep (Sweep Algorithm) — Khởi tạo Lời giải Ban đầu.
    - Tính góc cực (Polar Angle) của từng trạm so với Depot/CTU.
    - Sắp xếp trạm theo góc cực tăng dần.
    - Phân cụm trạm vào từng xe dựa trên TỔNG NHU CẦU SINH VIÊN (Student Demand),
      ĐẢM BẢO KHÔNG VƯỢT QUÁ CAPACITY CỦA XE (45 chỗ).
    """

    @staticmethod
    def calculate_polar_angle(depot_lat: float, depot_lng: float, point_lat: float, point_lng: float) -> float:
        """
        Tính góc cực theta_i = atan2(lat_i - lat_0, lng_i - lng_0) mod 2pi
        """
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
        depot_lat = depot.get("lat", depot.get("latitude", 10.0302))
        depot_lng = depot.get("lng", depot.get("longitude", 105.7721))

        total_dist = 0.0
        curr_lat, curr_lng = depot_lat, depot_lng
        for s in stops:
            s_lat = s.get("lat", s.get("latitude", s.get("location", {}).get("lat", 0.0)))
            s_lng = s.get("lng", s.get("longitude", s.get("location", {}).get("lng", 0.0)))
            total_dist += self.calculate_distance_km(curr_lat, curr_lng, s_lat, s_lng)
            curr_lat, curr_lng = s_lat, s_lng

        total_dist += self.calculate_distance_km(curr_lat, curr_lng, depot_lat, depot_lng)
        travel_time_min = (total_dist / average_speed_km_h) * 60.0
        dwell_time_min = len(stops) * 1.0
        return travel_time_min + dwell_time_min

    def create_initial_routes(
        self,
        depot: Dict[str, Any],
        stations: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        max_route_duration_minutes: float = 90.0,
        max_passenger_capacity: int = config.VEHICLE_CAPACITY,
        enforce_min_vehicles_for_60_students: bool = True
    ) -> List[List[Dict[str, Any]]]:
        """
        Input:
            depot: {"id": "SCHOOL", "lat": 10.0302, "lng": 105.7721}
            stations: [{"id": "ST-01", "name": "...", "lat": 10.04, "lng": 105.76, "pickup_student_count": 20, ...}]
            vehicles: [{"id": "BUS-01", "capacity": 45}, ...]
            max_route_duration_minutes: Giới hạn thời lượng toàn tuyến (<= 90 phút theo yêu cầu validation Ngày 9)
            max_passenger_capacity: Sức chứa tối đa (<= 45 khách)
        Output:
            Danh sách các route ban đầu (mỗi route là danh sách các trạm dừng):
            [[station1, station2], [station3, station4], ...]
        """
        if not stations or not vehicles:
            return []

        depot_lat = depot.get("lat", depot.get("latitude", 10.0302))
        depot_lng = depot.get("lng", depot.get("longitude", 105.7721))

        total_demand = sum(
            st.get("demand", st.get("pickup_student_count", st.get("student_count", 1)))
            for st in stations
        )

        # 1. Tính góc cực cho từng trạm
        stations_with_angle = []
        for st in stations:
            st_lat = st.get("lat", st.get("latitude", st.get("location", {}).get("lat", 0.0)))
            st_lng = st.get("lng", st.get("longitude", st.get("location", {}).get("lng", 0.0)))

            angle = self.calculate_polar_angle(depot_lat, depot_lng, st_lat, st_lng)
            st_copy = dict(st)
            st_copy["polar_angle"] = angle
            stations_with_angle.append(st_copy)

        # 2. Sắp xếp các trạm theo góc cực tăng dần (0 đến 360 độ)
        sorted_stations = sorted(stations_with_angle, key=lambda x: x["polar_angle"])

        effective_vehicles = [dict(v) for v in vehicles]
        if enforce_min_vehicles_for_60_students and total_demand >= 60 and len(effective_vehicles) >= 2:
            for v in effective_vehicles:
                v["capacity"] = min(v.get("capacity", max_passenger_capacity), max_passenger_capacity)

        # 3. Phân cụm theo tổng sinh viên demand <= capacity VÀ duration <= 90 phút
        routes: List[List[Dict[str, Any]]] = []
        vehicle_idx = 0

        current_route: List[Dict[str, Any]] = []
        current_demand = 0
        current_capacity = min(effective_vehicles[0].get("capacity", max_passenger_capacity), max_passenger_capacity)

        for st in sorted_stations:
            st_demand = st.get("demand", st.get("pickup_student_count", st.get("student_count", 1)))
            if st_demand <= 0:
                st_demand = 1

            # Kiểm tra:
            # 1. Quá tải (Capacity constraint)
            would_overload = (current_demand + st_demand > current_capacity)

            # 2. Quá giờ (Duration constraint <= 90 mins)
            candidate_stops = current_route + [st]
            est_duration = self.estimate_route_duration(depot, candidate_stops)
            would_overtime = (est_duration > max_route_duration_minutes) and (len(current_route) > 0)

            if would_overload or would_overtime:
                if current_route:
                    routes.append(current_route)

                vehicle_idx += 1
                if vehicle_idx < len(effective_vehicles):
                    current_capacity = min(effective_vehicles[vehicle_idx].get("capacity", max_passenger_capacity), max_passenger_capacity)
                else:
                    current_capacity = max_passenger_capacity

                current_route = []
                current_demand = 0

            current_route.append(st)
            current_demand += st_demand

        if current_route:
            routes.append(current_route)

        # Đảm bảo nếu total_demand >= 60 và len(effective_vehicles) >= 2 thì kết quả phải có >= 2 cụm xe
        if total_demand >= 60 and len(routes) < 2 and len(effective_vehicles) >= 2:
            single_route = routes[0]
            mid_idx = len(single_route) // 2
            routes = [single_route[:mid_idx], single_route[mid_idx:]]

        return routes
