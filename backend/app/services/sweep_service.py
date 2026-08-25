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

    def cluster_locations(
        self,
        depot: Dict[str, Any],
        locations: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Input:
            depot: {"id": 0, "latitude": float, "longitude": float}
            locations: [{"id": 1, "latitude": float, "longitude": float, "demand": int, ...}]
            vehicles: [{"id": 1, "capacity": int, ...}]
        Output:
            Danh sách cụm xe: [{"vehicle_id": 1, "capacity": 30, "stops": [loc1, loc2, ...]}, ...]
        """
        if not locations or not vehicles:
            return []

        # 1. Tính góc cực cho từng location
        depot_lat = depot["latitude"]
        depot_lng = depot["longitude"]

        locations_with_angle = []
        for loc in locations:
            angle = self.calculate_polar_angle(depot_lat, depot_lng, loc["latitude"], loc["longitude"])
            loc_copy = dict(loc)
            loc_copy["polar_angle"] = angle
            locations_with_angle.append(loc_copy)

        # 2. Sắp xếp các điểm đón theo góc cực tăng dần
        sorted_locations = sorted(locations_with_angle, key=lambda x: x["polar_angle"])

        # 3. Gom cụm theo sức chứa từng xe
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

            if current_cluster["current_demand"] + loc_demand > current_cluster["capacity"]:
                if vehicle_index + 1 < len(vehicles):
                    clusters.append(current_cluster)
                    vehicle_index += 1
                    current_vehicle = vehicles[vehicle_index]
                    current_cluster = {
                        "vehicle_id": current_vehicle["id"],
                        "capacity": current_vehicle["capacity"],
                        "current_demand": 0,
                        "stops": []
                    }
                else:
                    # Nếu đã hết xe buýt, đành nhồi nhét vào xe cuối cùng
                    pass

            current_cluster["stops"].append(loc)
            current_cluster["current_demand"] += loc_demand

        if current_cluster["stops"] and current_cluster not in clusters:
            clusters.append(current_cluster)

        return clusters
