import math
import random
from typing import List, Dict, Any, Tuple
from app.services.tabu_structures import TabuList, SwapMove, TwoOptMove

class RouteEvaluation:
    """
    Kết quả lượng giá chi tiết của một lộ trình xe buýt.
    """
    def __init__(self, distance: float, waiting_time: float, lateness: float, cost: float):
        self.distance = distance          # Tổng quãng đường di chuyển (km)
        self.waiting_time = waiting_time  # Tổng thời gian phải chờ do đến sớm (phút)
        self.lateness = lateness          # Tổng thời gian đến trễ sau time_window_end (phút)
        self.cost = cost                  # Điểm lượng giá Fitness tổng hợp (càng nhỏ càng tốt)

    def __repr__(self) -> str:
        return (f"RouteEvaluation(distance={self.distance:.2f}km, "
                f"waiting_time={self.waiting_time:.2f}m, "
                f"lateness={self.lateness:.2f}m, cost={self.cost:.2f})")


class TabuSearchOptimizer:
    """
    Giai đoạn 2: Thuật toán Tabu Search (Tối ưu lộ trình & Ràng buộc thời gian VRPTW)
    - Tối ưu thứ tự lộ trình cho từng cụm xe từ giai đoạn Sweep.
    - Ràng buộc: time_window_start, time_window_end tại từng điểm đón.
    - Tìm kiếm lân cận (2-Opt / Swap) kết hợp danh sách Tabu (Tabu List) để tránh kẹt tối ưu địa phương.
    - Đã nâng cấp các cơ chế: Dừng sớm (Early Stopping), Tabu Tenure Động và Đa dạng hóa (Diversification).
    """

    def __init__(
        self,
        tabu_tenure: int = 10,
        max_iterations: int = 100,
        distance_weight: float = 1.0,
        waiting_time_weight: float = 0.5,
        lateness_weight: float = 100.0,
        average_speed_km_h: float = 30.0,
        early_stopping_rounds: int = 30,
        diversify_rounds: int = 15
    ):
        self.tabu_tenure = tabu_tenure
        self.max_iterations = max_iterations
        self.distance_weight = distance_weight
        self.waiting_time_weight = waiting_time_weight
        self.lateness_weight = lateness_weight
        self.average_speed_km_h = average_speed_km_h
        self.early_stopping_rounds = early_stopping_rounds
        self.diversify_rounds = diversify_rounds

    @staticmethod
    def calculate_distance(p1: Dict[str, Any], p2: Dict[str, Any]) -> float:
        """Tính khoảng cách Haversine hoặc Euclidean giữa 2 tọa độ"""
        lat1, lng1 = p1["latitude"], p1["longitude"]
        lat2, lng2 = p2["latitude"], p2["longitude"]
        # Đơn vị xấp xỉ km
        return math.sqrt((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2) * 111.0

    def evaluate_route(self, route: List[Dict[str, Any]], depot: Dict[str, Any]) -> RouteEvaluation:
        """
        Hàm lượng giá (Cost/Fitness function) cho VRPTW:
        - Tính toán thời gian đi dựa trên khoảng cách và vận tốc trung bình.
        - Tính toán thời gian chờ nếu xe đến sớm hơn time_window_start.
        - Tính toán thời gian trễ và hình phạt nếu xe đến sau time_window_end.
        - Trả về đối tượng RouteEvaluation chứa thông tin phân rã chi tiết.
        """
        total_distance = 0.0
        total_waiting_time = 0.0
        total_lateness = 0.0
        
        current_time = 0.0  # tính bằng phút từ lúc xuất phát
        current_point = depot

        for stop in route:
            # 1. Tính khoảng cách và thời gian di chuyển
            dist = self.calculate_distance(current_point, stop)
            total_distance += dist
            
            # Thời gian đi (phút) = (khoảng cách km / vận tốc km/h) * 60 phút/giờ
            travel_time = (dist / self.average_speed_km_h) * 60.0
            current_time += travel_time

            # 2. Kiểm tra ràng buộc khung thời gian (Time Window)
            tw_start = stop.get("time_window_start")
            tw_end = stop.get("time_window_end")

            if tw_start is not None and current_time < tw_start:
                # Đến sớm -> Phải chờ
                wait_time = tw_start - current_time
                total_waiting_time += wait_time
                current_time = tw_start
            elif tw_end is not None and current_time > tw_end:
                # Đến trễ -> Tính thời gian trễ
                lateness_time = current_time - tw_end
                total_lateness += lateness_time

            current_point = stop

        # 3. Cộng khoảng cách quay về Depot
        return_dist = self.calculate_distance(current_point, depot)
        total_distance += return_dist
        
        # 4. Tính toán Fitness Cost tổng hợp
        total_cost = (
            (total_distance * self.distance_weight) +
            (total_waiting_time * self.waiting_time_weight) +
            (total_lateness * self.lateness_weight)
        )

        return RouteEvaluation(
            distance=total_distance,
            waiting_time=total_waiting_time,
            lateness=total_lateness,
            cost=total_cost
        )

    def optimize_cluster_route(self, cluster_stops: List[Dict[str, Any]], depot: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float]:
        """
        Tối ưu thứ tự điểm dừng cho 1 cụm xe bằng thuật toán Tabu Search hoàn chỉnh đã được nâng cấp:
        - Tích hợp Tabu Tenure Động dựa trên số lượng điểm dừng (n).
        - Tích hợp cơ chế Dừng sớm (Early Stopping) nếu cost không cải thiện.
        - Tích hợp cơ chế Đa dạng hóa (Diversification) thực hiện Random Walk khi bị kẹt tối ưu địa phương.
        """
        if len(cluster_stops) <= 2:
            eval_res = self.evaluate_route(cluster_stops, depot)
            return cluster_stops, eval_res.cost

        n = len(cluster_stops)

        # Khởi tạo giải pháp tốt nhất ban đầu
        best_solution = list(cluster_stops)
        best_eval = self.evaluate_route(best_solution, depot)
        best_cost = best_eval.cost

        current_solution = list(best_solution)
        
        # 1. Tính Tabu Tenure Động: tỷ lệ thuận với số trạm dừng (tối thiểu là 3)
        base_tenure = max(3, min(int(n * 0.4), 15))
        tabu_list = TabuList(tenure=base_tenure)

        iterations_without_improvement = 0

        for iteration in range(self.max_iterations):
            # Biến động ngẫu nhiên tenure nhẹ (+-1) sau mỗi vòng lặp để phá thế tuần hoàn
            tabu_list.tenure = max(3, base_tenure + random.choice([-1, 0, 1]))

            best_neighbor = None
            best_neighbor_cost = float("inf")
            best_move = None
            
            # 2. Sinh không gian lân cận (Neighborhood moves)
            candidate_moves = []
            
            # Phép hoán đổi Swap(i, j) cho mọi cặp điểm đón i < j
            for i in range(n - 1):
                for j in range(i + 1, n):
                    candidate_moves.append(SwapMove(i, j))
            
            # Phép hoán đổi 2-Opt(i, j) cho mọi cặp điểm đón i < j (với j - i >= 2 để tránh trùng với swap kề)
            for i in range(n - 2):
                for j in range(i + 2, n):
                    candidate_moves.append(TwoOptMove(i, j))

            if len(candidate_moves) > 60:
                candidate_moves = random.sample(candidate_moves, 60)

            # 3. Đánh giá tất cả các nước đi trong không gian lân cận
            for move in candidate_moves:
                neighbor_solution = move.apply(current_solution)
                neighbor_eval = self.evaluate_route(neighbor_solution, depot)
                neighbor_cost = neighbor_eval.cost

                # Kiểm tra xem nước đi có bị cấm (tabu) không
                # Aspiration criteria được tự động xử lý bên trong is_tabu (bỏ qua cấm nếu neighbor_cost < best_cost)
                if not tabu_list.is_tabu(move, iteration, neighbor_cost, best_cost):
                    if neighbor_cost < best_neighbor_cost:
                        best_neighbor = neighbor_solution
                        best_neighbor_cost = neighbor_cost
                        best_move = move

            # 4. Kiểm tra kẹt tối ưu địa phương hoặc hội tụ sớm
            if best_neighbor is None or best_neighbor_cost >= best_cost:
                iterations_without_improvement += 1
            else:
                iterations_without_improvement = 0

            # --- Cơ chế Đa dạng hóa (Diversification - Random Walk) ---
            # Nếu quá lâu không cải thiện (đạt diversify_rounds) mà chưa đến ngưỡng dừng hẳn
            if iterations_without_improvement == self.diversify_rounds:
                # Thực hiện một bước di chuyển ngẫu nhiên để nhảy khỏi hố tối ưu
                random_move = random.choice(candidate_moves)
                current_solution = random_move.apply(current_solution)
                tabu_list.add_move(random_move, iteration)
                
                # Cập nhật chi phí cho giải pháp ngẫu nhiên mới này
                random_eval = self.evaluate_route(current_solution, depot)
                
                # Reset đếm không cải thiện để tiếp tục tìm kiếm vùng mới
                iterations_without_improvement = 0
                
                if random_eval.cost < best_cost:
                    best_solution = list(current_solution)
                    best_cost = random_eval.cost
                continue

            # --- Cơ chế Dừng sớm (Early Stopping) ---
            if iterations_without_improvement >= self.early_stopping_rounds:
                # Đã hội tụ và không có tiến triển gì thêm
                break

            # Nếu không tìm thấy nước đi hợp lệ nào và không kích hoạt diversification
            if best_neighbor is None:
                break

            # Cập nhật giải pháp hiện tại
            current_solution = best_neighbor
            
            # Đưa nước đi vừa chọn vào Tabu List
            tabu_list.add_move(best_move, iteration)

            # Cập nhật giải pháp tốt nhất toàn cục
            if best_neighbor_cost < best_cost:
                best_solution = list(best_neighbor)
                best_cost = best_neighbor_cost

        return best_solution, best_cost

