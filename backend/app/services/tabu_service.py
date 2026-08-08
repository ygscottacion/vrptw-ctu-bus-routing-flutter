import math
from typing import List, Dict, Any, Tuple

class TabuSearchOptimizer:
    """
    Giai đoạn 2: Thuật toán Tabu Search (Tối ưu lộ trình & Ràng buộc thời gian VRPTW)
    - Tối ưu thứ tự lộ trình cho từng cụm xe từ giai đoạn Sweep.
    - Ràng buộc: time_window_start, time_window_end tại từng điểm đón.
    - Tìm kiếm lân cận (2-Opt / Swap) kết hợp danh sách Tabu (Tabu List) để tránh kẹt tối ưu địa phương.
    """

    def __init__(self, tabu_tenure: int = 10, max_iterations: int = 100):
        self.tabu_tenure = tabu_tenure
        self.max_iterations = max_iterations

    @staticmethod
    def calculate_distance(p1: Dict[str, Any], p2: Dict[str, Any]) -> float:
        """Tính khoảng cách Euclidean hoặc Haversine giữa 2 tọa độ"""
        lat1, lng1 = p1["latitude"], p1["longitude"]
        lat2, lng2 = p2["latitude"], p2["longitude"]
        # Đơn vị xấp xỉ km
        return math.sqrt((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2) * 111.0

    def evaluate_route(self, route: List[Dict[str, Any]], depot: Dict[str, Any]) -> float:
        """
        Hàm lượng giá (Cost function):
        = Tổng khoảng cách + Hình phạt vi phạm Khung thời gian (Time Windows)
        """
        total_cost = 0.0
        current_time = 0.0  # phút/giờ
        current_point = depot

        for stop in route:
            dist = self.calculate_distance(current_point, stop)
            total_cost += dist
            current_time += dist * 2  # Giả định 2 phút / 1 km trong nội ô

            # Kiểm tra ràng buộc khung thời gian (Time Window)
            tw_start = stop.get("time_window_start")
            tw_end = stop.get("time_window_end")

            if tw_start and current_time < tw_start:
                # Xe đến sớm -> phải chờ
                current_time = tw_start
            elif tw_end and current_time > tw_end:
                # Xe đến trễ -> cộng hình phạt (penalty) lớn
                penalty = (current_time - tw_end) * 100.0
                total_cost += penalty

            current_point = stop

        # Cộng khoảng cách quay về Depot
        total_cost += self.calculate_distance(current_point, depot)
        return total_cost

    def optimize_cluster_route(self, cluster_stops: List[Dict[str, Any]], depot: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float]:
        """Tối ưu thứ tự điểm dừng cho 1 cụm xe bằng Tabu Search"""
        if len(cluster_stops) <= 2:
            cost = self.evaluate_route(cluster_stops, depot)
            return cluster_stops, cost

        best_solution = list(cluster_stops)
        best_cost = self.evaluate_route(best_solution, depot)

        current_solution = list(best_solution)
        tabu_list = {}  # Format: (i, j) -> expire_iteration

        for iteration in range(self.max_iterations):
            best_neighbor = None
            best_neighbor_cost = float("inf")
            best_move = None

            # Tạo không gian lân cận bằng phép hoán đổi 2-Opt (Swap)
            n = len(current_solution)
            for i in range(n - 1):
                for j in range(i + 1, n):
                    neighbor = list(current_solution)
                    neighbor[i], neighbor[j] = neighbor[j], neighbor[i]

                    cost = self.evaluate_route(neighbor, depot)
                    move = (i, j)

                    # Kiểm tra nếu move nằm trong Tabu List và không thỏa Aspiration Criteria
                    is_tabu = tabu_list.get(move, 0) > iteration
                    if not is_tabu or cost < best_cost:
                        if cost < best_neighbor_cost:
                            best_neighbor = neighbor
                            best_neighbor_cost = cost
                            best_move = move

            if best_neighbor is None:
                break

            current_solution = best_neighbor
            if best_move:
                tabu_list[best_move] = iteration + self.tabu_tenure

            if best_neighbor_cost < best_cost:
                best_solution = list(best_neighbor)
                best_cost = best_neighbor_cost

        return best_solution, best_cost
