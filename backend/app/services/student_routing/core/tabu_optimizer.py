import random
import copy
from typing import List, Dict, Any, Tuple
from app.services.student_routing import config
from app.services.student_routing.core.evaluator import SolutionEvaluator, EvaluationResult


class TabuList:
    """
    Quản lý danh sách cấm (Tabu List) với Dynamic Tenure và Aspiration Criterion.
    """
    def __init__(self, base_tenure: int = config.TABU_TENURE_BASE):
        self.tenure = base_tenure
        self.tabu_dict: Dict[Tuple[str, Any, Any], int] = {}

    def add_move(self, move_key: Tuple[str, Any, Any], current_iteration: int) -> None:
        self.tabu_dict[move_key] = current_iteration + self.tenure

    def is_tabu(
        self,
        move_key: Tuple[str, Any, Any],
        current_iteration: int,
        candidate_objective: float,
        best_objective: float
    ) -> bool:
        expired_iteration = self.tabu_dict.get(move_key, 0)
        if expired_iteration > current_iteration:
            # Aspiration Criterion: Bỏ cấm nếu candidate_objective tốt hơn hẳn best_objective
            if candidate_objective < best_objective:
                return False
            return True
        return False

    def clear(self) -> None:
        self.tabu_dict.clear()


class TabuSearchOptimizer:
    """
    Thuật toán Tabu Search (Tabu Search Optimization Engine):
    - Nhận Lời giải Ban đầu (Initial Solution) từ Sweep Clusterer.
    - Sinh Neighborhood bằng 3 phép toán: Swap, Relocate, và 2-Opt.
    - Đánh giá tất cả giải pháp bằng SolutionEvaluator.
    - Quản lý Tabu List với Tenure động, Aspiration Criterion, Early Stopping và Diversification.
    - Trả về Giải pháp Tối ưu nhất (Best Solution).
    """

    def __init__(
        self,
        evaluator: SolutionEvaluator = None,
        max_iterations: int = config.TABU_MAX_ITERATIONS,
        base_tenure: int = config.TABU_TENURE_BASE,
        early_stopping_rounds: int = config.EARLY_STOPPING_ROUNDS,
        diversify_rounds: int = config.DIVERSIFY_ROUNDS
    ):
        self.evaluator = evaluator or SolutionEvaluator()
        self.max_iterations = max_iterations
        self.base_tenure = base_tenure
        self.early_stopping_rounds = early_stopping_rounds
        self.diversify_rounds = diversify_rounds

    def generate_neighborhood(
        self,
        routes: List[List[Dict[str, Any]]]
    ) -> List[Tuple[List[List[Dict[str, Any]]], Tuple[str, Any, Any]]]:
        """
        Sinh các giải pháp lân cận (Neighborhood Candidates) cùng với key đại diện cho nước đi.
        Bao gồm:
        1. Swap (Hoán đổi 2 trạm trong cùng route hoặc giữa 2 route)
        2. Relocate (Di chuyển 1 trạm sang vị trí khác)
        3. 2-Opt (Đảo ngược đoạn con trong 1 route)
        """
        candidates = []
        num_routes = len(routes)

        # ── 1. Intra-route 2-Opt ──────────────────────────────────────────────
        for r_idx in range(num_routes):
            route = routes[r_idx]
            n = len(route)
            if n >= 4:
                for i in range(n - 2):
                    for j in range(i + 2, n):
                        new_routes = [copy.deepcopy(r) for r in routes]
                        new_routes[r_idx][i:j + 1] = reversed(new_routes[r_idx][i:j + 1])
                        move_key = ("2opt", r_idx, (i, j))
                        candidates.append((new_routes, move_key))

        # ── 2. Intra-route & Inter-route Swap ──────────────────────────────────
        for r1 in range(num_routes):
            for r2 in range(r1, num_routes):
                route1 = routes[r1]
                route2 = routes[r2]
                n1 = len(route1)
                n2 = len(route2)

                for i in range(n1):
                    start_j = i + 1 if r1 == r2 else 0
                    for j in range(start_j, n2):
                        new_routes = [copy.deepcopy(r) for r in routes]
                        st1 = new_routes[r1][i]
                        st2 = new_routes[r2][j]
                        new_routes[r1][i] = st2
                        new_routes[r2][j] = st1

                        st1_id = st1.get("id", i)
                        st2_id = st2.get("id", j)
                        move_key = ("swap", min(st1_id, st2_id), max(st1_id, st2_id))
                        candidates.append((new_routes, move_key))

        # ── 3. Inter-route & Intra-route Relocate ──────────────────────────────
        for r1 in range(num_routes):
            for r2 in range(num_routes):
                route1 = routes[r1]
                n1 = len(route1)

                if n1 <= 1 and r1 == r2:
                    continue

                for i in range(n1):
                    target_route = routes[r2]
                    n2 = len(target_route)
                    insert_positions = range(n2 + 1) if r1 != r2 else range(n2)

                    for pos in insert_positions:
                        if r1 == r2 and (pos == i or pos == i + 1):
                            continue

                        new_routes = [copy.deepcopy(r) for r in routes]
                        st = new_routes[r1].pop(i)
                        new_routes[r2].insert(pos if r1 != r2 or pos < i else pos - 1, st)

                        # Clean up empty routes if inter-route move
                        new_routes = [r for r in new_routes if len(r) > 0]

                        st_id = st.get("id", i)
                        move_key = ("relocate", st_id, (r2, pos))
                        candidates.append((new_routes, move_key))

        # Khống chế mẫu không gian lân cận tối đa 80 candidates để tối ưu thời gian chạy
        if len(candidates) > 80:
            candidates = random.sample(candidates, 80)

        return candidates

    def optimize(
        self,
        initial_routes: List[List[Dict[str, Any]]],
        depot: Dict[str, Any],
        distance_matrix: List[List[float]],
        travel_time_matrix: List[List[float]],
        point_index_map: Dict[str, int],
        vehicle_capacities: List[int] = None,
        departure_time_mins: float = 330.0
    ) -> Tuple[List[List[Dict[str, Any]]], EvaluationResult]:
        """
        Thực thi thuật toán Tabu Search để tối ưu Initial Solution từ Sweep.
        """
        if not initial_routes:
            eval_res = self.evaluator.evaluate_solution(
                [], depot, distance_matrix, travel_time_matrix, point_index_map, vehicle_capacities, departure_time_mins
            )
            return [], eval_res

        current_solution = copy.deepcopy(initial_routes)
        best_solution = copy.deepcopy(initial_routes)

        best_eval = self.evaluator.evaluate_solution(
            best_solution, depot, distance_matrix, travel_time_matrix, point_index_map, vehicle_capacities, departure_time_mins
        )

        tabu_list = TabuList(base_tenure=self.base_tenure)
        rounds_without_improvement = 0

        for iteration in range(self.max_iterations):
            # Dynamic tenure jitter (+-1)
            tabu_list.tenure = max(3, self.base_tenure + random.choice([-1, 0, 1]))

            candidates = self.generate_neighborhood(current_solution)
            if not candidates:
                break

            best_candidate_routes = None
            best_candidate_eval = None
            best_candidate_move = None
            best_candidate_obj = float("inf")

            for candidate_routes, move_key in candidates:
                cand_eval = self.evaluator.evaluate_solution(
                    candidate_routes, depot, distance_matrix, travel_time_matrix, point_index_map, vehicle_capacities, departure_time_mins
                )

                if not tabu_list.is_tabu(move_key, iteration, cand_eval.objective_value, best_eval.objective_value):
                    if cand_eval.objective_value < best_candidate_obj:
                        best_candidate_routes = candidate_routes
                        best_candidate_eval = cand_eval
                        best_candidate_move = move_key
                        best_candidate_obj = cand_eval.objective_value

            # Cập nhật state
            if best_candidate_routes is None:
                rounds_without_improvement += 1
            else:
                current_solution = best_candidate_routes
                tabu_list.add_move(best_candidate_move, iteration)

                if best_candidate_eval.objective_value < best_eval.objective_value:
                    best_solution = copy.deepcopy(best_candidate_routes)
                    best_eval = best_candidate_eval
                    rounds_without_improvement = 0
                else:
                    rounds_without_improvement += 1

            # ── Cơ chế Đa dạng hóa (Diversification / Random Walk) ───────────
            if rounds_without_improvement == self.diversify_rounds and candidates:
                rand_routes, rand_move = random.choice(candidates)
                current_solution = rand_routes
                tabu_list.add_move(rand_move, iteration)
                rounds_without_improvement = 0

            # ── Cơ chế Dừng sớm (Early Stopping) ─────────────────────────────
            if rounds_without_improvement >= self.early_stopping_rounds:
                break

        return best_solution, best_eval
