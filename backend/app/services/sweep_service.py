import math
from typing import List, Dict, Any

class SweepClusteringService:
    """
    Giai đoạn 1 & 2: Thuật toán Sweep (Quét theo góc cực và Gom cụm)
    - Nhận vào Depot (trạm xuất phát tâm), danh sách các điểm đón (Locations) và danh sách Xe buýt (Vehicles).
    - Tính góc cực (Polar Angle) của từng điểm đón so với Depot.
    - Sắp xếp các điểm đón theo góc cực tăng dần (0 đến 360 độ / 0 đến 2π rad), ưu tiên điểm gần Depot hơn nếu cùng góc.
    - Gom cụm các điểm đón vào từng xe sao cho tổng nhu cầu (demand) <= sức chứa của xe (capacity).
    """

    @staticmethod
    def calculate_polar_angle(
        depot_lat: float,
        depot_lng: float,
        point_lat: float,
        point_lng: float,
        start_angle_rad: float = 0.0
    ) -> float:
        """
        Tính góc cực (tính bằng Radian, từ 0 đến 2π) giữa điểm đón và Depot tâm.
        Cho phép dịch chuyển góc quét bắt đầu bằng start_angle_rad.
        """
        d_lat = point_lat - depot_lat
        d_lng = point_lng - depot_lng
        angle = math.atan2(d_lat, d_lng) - start_angle_rad
        angle = angle % (2 * math.pi)
        if angle < 0:
            angle += 2 * math.pi
        return angle

    @staticmethod
    def calculate_distance_to_depot(
        depot_lat: float,
        depot_lng: float,
        point_lat: float,
        point_lng: float
    ) -> float:
        """Tính khoảng cách Euclidean giữa điểm đón và Depot (dùng để sắp xếp phụ)"""
        return math.hypot(point_lat - depot_lat, point_lng - depot_lng)

    def cluster_locations(
        self,
        depot: Dict[str, Any],
        locations: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        start_angle_rad: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Input:
            depot: {"id": 0, "latitude": float, "longitude": float}
            locations: [{"id": 1, "latitude": float, "longitude": float, "demand": int, ...}]
            vehicles: [{"id": 1, "capacity": int, ...}]
            start_angle_rad: Góc khởi đầu tính bằng Radian (mặc định 0.0)
        Output:
            Danh sách cụm xe: [{"vehicle_id": 1, "capacity": 30, "current_demand": 15, "stops": [loc1, loc2, ...]}, ...]
        """
        if not locations or not vehicles:
            return []

        depot_lat = depot["latitude"]
        depot_lng = depot["longitude"]

        # 1. Tính góc cực và khoảng cách tới Depot cho từng location
        locations_with_angle = []
        for loc in locations:
            angle = self.calculate_polar_angle(
                depot_lat, depot_lng, loc["latitude"], loc["longitude"], start_angle_rad
            )
            dist = self.calculate_distance_to_depot(
                depot_lat, depot_lng, loc["latitude"], loc["longitude"]
            )
            loc_copy = dict(loc)
            loc_copy["polar_angle"] = angle
            loc_copy["distance_to_depot"] = dist
            locations_with_angle.append(loc_copy)

        # 2. Sắp xếp các điểm đón theo góc cực tăng dần (nếu cùng góc, xếp theo khoảng cách gần Depot hơn trước)
        sorted_locations = sorted(
            locations_with_angle,
            key=lambda x: (x["polar_angle"], x["distance_to_depot"])
        )

        # 3. Gom cụm theo sức chứa (capacity) của từng xe buýt
        clusters = []
        vehicle_index = 0
        current_vehicle = vehicles[vehicle_index]
        current_cluster = {
            "vehicle_id": current_vehicle["id"],
            "capacity": current_vehicle["capacity"],
            "current_demand": 0,
            "stops": []
        }

        for loc in sorted_locations:
            loc_demand = loc.get("demand", 1)

            # Nếu thêm điểm này mà vượt quá capacity của xe hiện tại -> chuyển sang xe tiếp theo
            if current_cluster["current_demand"] + loc_demand > current_cluster["capacity"]:
                if current_cluster["stops"]:
                    clusters.append(current_cluster)
                
                vehicle_index += 1

                if vehicle_index >= len(vehicles):
                    # Hết xe buýt có sẵn -> gán vào cụm cuối cùng (sẽ được xử lý bởi outlier handler ở tuần 3)
                    current_cluster = clusters[-1] if clusters else {
                        "vehicle_id": current_vehicle["id"],
                        "capacity": current_vehicle["capacity"],
                        "current_demand": 0,
                        "stops": []
                    }
                else:
                    current_vehicle = vehicles[vehicle_index]
                    current_cluster = {
                        "vehicle_id": current_vehicle["id"],
                        "capacity": current_vehicle["capacity"],
                        "current_demand": 0,
                        "stops": []
                    }

            current_cluster["stops"].append(loc)
            current_cluster["current_demand"] += loc_demand

        if current_cluster["stops"] and current_cluster not in clusters:
            clusters.append(current_cluster)

        return clusters

