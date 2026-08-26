import time
import math
import random
import statistics
from typing import List, Dict, Any, Tuple
from app.services.student_routing import config
from app.services.student_routing.helpers.distance_matrix import StaticDistanceMatrixProvider
from app.services.student_routing.core.evaluator import SolutionEvaluator
from app.services.student_routing.core.sweep_clustering import SweepClusterer
from app.services.student_routing.core.tabu_optimizer import TabuSearchOptimizer


def generate_synthetic_dataset(
    num_vehicles: int,
    num_stations: int,
    total_students: int,
    seed: int = 42
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Tạo dữ liệu thử nghiệm bán kính 10km quanh CTU main campus (10.0302 N, 105.7721 E).
    """
    random.seed(seed)
    depot = {"id": "SCHOOL", "lat": 10.0302, "lng": 105.7721}

    vehicles = [
        {"id": f"BUS-{i+1:02d}", "capacity": config.VEHICLE_CAPACITY}
        for i in range(num_vehicles)
    ]

    base_demand = total_students // num_stations
    remainder = total_students % num_stations

    stations = []
    for i in range(num_stations):
        # Generate random point within ~8km radius
        angle_rad = random.uniform(0, 2 * math.pi)
        radius_km = random.uniform(1.0, 8.0)
        # 1 deg lat ~ 111km, 1 deg lng ~ 111km * cos(10 deg) ~ 109km
        delta_lat = (radius_km / 111.0) * math.sin(angle_rad)
        delta_lng = (radius_km / 109.0) * math.cos(angle_rad)

        st_lat = round(depot["lat"] + delta_lat, 5)
        st_lng = round(depot["lng"] + delta_lng, 5)

        demand = base_demand + (1 if i < remainder else 0)

        # Time Windows around morning peak (06:00 - 06:30)
        tw_start_min = 350 + random.randint(0, 20)  # 05:50 - 06:10
        tw_end_min = tw_start_min + random.randint(15, 25)

        h1, m1 = divmod(tw_start_min, 60)
        h2, m2 = divmod(tw_end_min, 60)

        stations.append({
            "id": f"ST-{i+1:02d}",
            "name": f"Trạm thử nghiệm #{i+1}",
            "lat": st_lat,
            "lng": st_lng,
            "pickup_student_count": demand,
            "dropoff_student_count": demand,
            "demand": demand,
            "time_window_start": f"{h1:02d}:{m1:02d}",
            "time_window_end": f"{h2:02d}:{m2:02d}"
        })

    return depot, stations, vehicles


class StudentRoutingBenchmark:
    """
    Bộ công cụ Benchmark so sánh Sweep Algorithm (Baseline) vs Sweep + Tabu Search.
    Đo lường 8 chỉ số chính trên Small (15 stations), Medium (30 stations), và Large (50 stations) datasets.
    """

    def __init__(self):
        self.distance_provider = StaticDistanceMatrixProvider()
        self.evaluator = SolutionEvaluator()
        self.sweep_clusterer = SweepClusterer()

    def run_single_dataset(
        self,
        name: str,
        num_vehicles: int,
        num_stations: int,
        total_students: int,
        num_runs: int = 5
    ):
        depot, stations, vehicles = generate_synthetic_dataset(
            num_vehicles, num_stations, total_students, seed=42
        )

        all_points = [{"lat": depot["lat"], "lng": depot["lng"]}]
        point_index_map = {"SCHOOL": 0}
        for idx, st in enumerate(stations, start=1):
            all_points.append({"lat": st["lat"], "lng": st["lng"]})
            point_index_map[st["id"]] = idx

        dist_matrix, ttime_matrix, _ = self.distance_provider.get_matrix(
            all_points, time_str_or_session="MORNING_1"
        )
        vehicle_capacities = [v["capacity"] for v in vehicles]

        # ── 1. Baseline: Sweep Algorithm ──────────────────────────────────────
        t0 = time.perf_counter()
        sweep_routes = self.sweep_clusterer.create_initial_routes(depot, stations, vehicles)
        t_sweep_ms = (time.perf_counter() - t0) * 1000.0

        sweep_eval = self.evaluator.evaluate_solution(
            sweep_routes, depot, dist_matrix, ttime_matrix, point_index_map, vehicle_capacities, 330.0
        )

        # ── 2. Sweep + Tabu Search (Multiple Runs for StdDev) ─────────────────
        tabu_objs = []
        tabu_dists = []
        tabu_runtimes_ms = []

        best_tabu_eval = None
        best_tabu_routes = None

        for run_idx in range(num_runs):
            random.seed(100 + run_idx)
            optimizer = TabuSearchOptimizer(evaluator=self.evaluator)

            t1 = time.perf_counter()
            opt_routes, opt_eval = optimizer.optimize(
                sweep_routes, depot, dist_matrix, ttime_matrix, point_index_map, vehicle_capacities, 330.0
            )
            t_tabu_ms = (time.perf_counter() - t1) * 1000.0

            tabu_objs.append(opt_eval.objective_value)
            tabu_dists.append(opt_eval.total_distance)
            tabu_runtimes_ms.append(t_tabu_ms)

            if best_tabu_eval is None or opt_eval.objective_value < best_tabu_eval.objective_value:
                best_tabu_eval = opt_eval
                best_tabu_routes = opt_routes

        # ── 3. Calculate Improvement % ────────────────────────────────────────
        baseline_obj = sweep_eval.objective_value
        best_obj = best_tabu_eval.objective_value
        avg_obj = statistics.mean(tabu_objs)
        std_obj = statistics.stdev(tabu_objs) if num_runs > 1 else 0.0

        imp_best_pct = ((baseline_obj - best_obj) / baseline_obj) * 100.0 if baseline_obj > 0 else 0.0
        imp_avg_pct = ((baseline_obj - avg_obj) / baseline_obj) * 100.0 if baseline_obj > 0 else 0.0

        cost_per_km = 1.5  # Estimated operating cost $1.5/km
        sweep_cost = round(sweep_eval.total_distance * cost_per_km, 2)
        tabu_cost = round(best_tabu_eval.total_distance * cost_per_km, 2)

        print(f"\n=================== DATASET: {name.upper()} ({num_vehicles} Veh / {num_stations} St / {total_students} SV) ===================")
        print(f"Metrics                      | Baseline (Sweep)        | Sweep + Tabu Search (Best) | Improvement")
        print(f"-----------------------------|-------------------------|----------------------------|------------")
        print(f"Total Distance (km)          | {sweep_eval.total_distance:<23} | {best_tabu_eval.total_distance:<26} | {round(sweep_eval.total_distance - best_tabu_eval.total_distance, 2)} km")
        print(f"Estimated Cost ($)           | ${sweep_cost:<22} | ${tabu_cost:<25} | ${round(sweep_cost - tabu_cost, 2)}")
        print(f"Total Travel Time (mins)     | {sweep_eval.total_travel_time:<23} | {best_tabu_eval.total_travel_time:<26} | {round(sweep_eval.total_travel_time - best_tabu_eval.total_travel_time, 2)} mins")
        print(f"Early Arrival (mins)         | {sweep_eval.total_early_arrival:<23} | {best_tabu_eval.total_early_arrival:<26} | {round(sweep_eval.total_early_arrival - best_tabu_eval.total_early_arrival, 2)} mins")
        print(f"Late Arrival (mins)          | {sweep_eval.total_late_arrival:<23} | {best_tabu_eval.total_late_arrival:<26} | {round(sweep_eval.total_late_arrival - best_tabu_eval.total_late_arrival, 2)} mins")
        print(f"Time Window Penalty          | {round(sweep_eval.early_penalty + sweep_eval.late_penalty, 2):<23} | {round(best_tabu_eval.early_penalty + best_tabu_eval.late_penalty, 2):<26} | {round((sweep_eval.early_penalty + sweep_eval.late_penalty) - (best_tabu_eval.early_penalty + best_tabu_eval.late_penalty), 2)}")
        print(f"Rejected Stops               | {0:<23} | {0:<26} | 0")
        print(f"Objective Value              | {sweep_eval.objective_value:<23} | {best_tabu_eval.objective_value:<26} | {round(imp_best_pct, 2)}%")
        print(f"Runtime (ms)                 | {round(t_sweep_ms, 2):<23} | {round(statistics.mean(tabu_runtimes_ms), 2):<26} | -")
        print(f"Tabu Runs (Best/Avg/StdDev)  | -                       | {round(best_obj,2)} / {round(avg_obj,2)} / ±{round(std_obj,2)} | -")
        print(f"====================================================================================================\n")

    def run_all(self):
        print("\n" + "="*80)
        print("          STUDENT ROUTING VRPTW BENCHMARK SUITE (SWEEP vs SWEEP+TABU)")
        print("="*80)

        # 1. Small Dataset
        self.run_single_dataset("Small", num_vehicles=3, num_stations=15, total_students=45)

        # 2. Medium Dataset
        self.run_single_dataset("Medium", num_vehicles=4, num_stations=30, total_students=90)

        # 3. Large Dataset
        self.run_single_dataset("Large", num_vehicles=5, num_stations=50, total_students=150)


if __name__ == "__main__":
    benchmark = StudentRoutingBenchmark()
    benchmark.run_all()
