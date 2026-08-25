from typing import List, Dict, Any
from app.services.sweep_service import SweepClusteringService
from app.services.tabu_service import TabuSearchOptimizer

class VRPTWSolverService:
    """
    Service tổng hợp VRPTW Solver Pipeline:
    Kết hợp Sweep Algorithm (Gom cụm) + Tabu Search (Tối ưu thứ tự lộ trình).
    """

    def __init__(self):
        self.sweep_service = SweepClusteringService()
        self.tabu_optimizer = TabuSearchOptimizer()

    def solve(
        self,
        depot: Dict[str, Any],
        locations: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Input:
            depot: {"id": 0, "name": "Depot CTU", "latitude": 10.03, "longitude": 105.77}
            locations: Danh sách trạm đón
            vehicles: Danh sách xe buýt
        Output:
            Danh sách các chuyến xe đã được phân bổ thứ tự tối ưu
        """
        # Bước 1: Sweep Algorithm - Gom cụm các điểm đón
        clusters = self.sweep_service.cluster_locations(depot, locations, vehicles)

        # Bước 2: Tabu Search - Tối ưu lộ trình từng cụm xe
        final_routes = []
        for cluster in clusters:
            optimized_stops, total_cost = self.tabu_optimizer.optimize_cluster_route(
                cluster["stops"], depot
            )
            # Đánh giá lại lộ trình đã tối ưu để lấy ra quãng đường thực tế (km)
            eval_res = self.tabu_optimizer.evaluate_route(optimized_stops, depot)

            final_routes.append({
                "vehicle_id": cluster["vehicle_id"],
                "total_demand": cluster["current_demand"],
                "total_distance_km": round(eval_res.distance, 2),
                "ordered_stops": [depot] + optimized_stops + [depot]
            })

        return final_routes
