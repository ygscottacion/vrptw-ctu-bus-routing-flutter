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

    def create_initial_routes(
        self,
        depot: Dict[str, Any],
        stations: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Input:
            depot: {"id": "SCHOOL", "lat": 10.0302, "lng": 105.7721}
            stations: [{"id": "ST-01", "name": "...", "lat": 10.04, "lng": 105.76, "pickup_student_count": 20, ...}]
            vehicles: [{"id": "BUS-01", "capacity": 45}, ...]
        Output:
            Danh sách các route ban đầu (mỗi route là danh sách các trạm dừng):
            [[station1, station2], [station3, station4], ...]
        """
        if not stations or not vehicles:
            return []

        depot_lat = depot.get("lat", depot.get("latitude", 10.0302))
        depot_lng = depot.get("lng", depot.get("longitude", 105.7721))

        # 1. Tính góc cực cho từng trạm
        stations_with_angle = []
        for st in stations:
            st_lat = st.get("lat", st.get("location", {}).get("lat", 0.0))
            st_lng = st.get("lng", st.get("location", {}).get("lng", 0.0))

            angle = self.calculate_polar_angle(depot_lat, depot_lng, st_lat, st_lng)
            st_copy = dict(st)
            st_copy["polar_angle"] = angle
            stations_with_angle.append(st_copy)

        # 2. Sắp xếp các trạm theo góc cực tăng dần (0 đến 360 độ)
        sorted_stations = sorted(stations_with_angle, key=lambda x: x["polar_angle"])

        # 3. Phân cụm theo tổng sinh viên demand <= capacity
        routes: List[List[Dict[str, Any]]] = []
        vehicle_idx = 0

        current_route: List[Dict[str, Any]] = []
        current_demand = 0
        current_capacity = vehicles[0].get("capacity", config.VEHICLE_CAPACITY)

        for st in sorted_stations:
            # Lấy số sinh viên đón/trả tại trạm này (demand)
            st_demand = st.get("demand", st.get("pickup_student_count", st.get("student_count", 1)))
            if st_demand <= 0:
                st_demand = 1  # Tối thiểu 1 nếu không có dữ liệu

            # Kiểm tra nếu thêm trạm này mà vượt quá capacity của xe hiện tại
            if current_demand + st_demand > current_capacity:
                if current_route:
                    routes.append(current_route)
                
                vehicle_idx += 1
                if vehicle_idx < len(vehicles):
                    current_capacity = vehicles[vehicle_idx].get("capacity", config.VEHICLE_CAPACITY)
                else:
                    # Nếu hết xe, tạo thêm route cho xe dư hoặc sử dụng xe cuối
                    current_capacity = config.VEHICLE_CAPACITY

                current_route = []
                current_demand = 0

            current_route.append(st)
            current_demand += st_demand

        if current_route:
            routes.append(current_route)

        return routes
