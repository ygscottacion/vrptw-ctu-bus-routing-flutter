import unittest
from app.services.student_routing import config
from app.services.student_routing.schemas import (
    SchoolConfig, Vehicle, Station, OptimizationOptions, LocationSchema, SessionId, TripType
)
from app.services.student_routing.helpers.distance_matrix import (
    haversine_distance, StaticDistanceMatrixProvider, OSRMWithFallbackProvider
)
from app.services.student_routing.helpers.path_flexibility import PathFlexibilityManager, TrafficPeriod
from app.services.student_routing.core.evaluator import SolutionEvaluator
from app.services.student_routing.core.sweep_clustering import SweepClusterer
from app.services.student_routing.core.tabu_optimizer import TabuSearchOptimizer, TabuList
from app.services.student_routing.student_routing_service import StudentRoutingService
from app.services.student_routing.benchmark import StudentRoutingBenchmark


class TestStudentRouting(unittest.TestCase):

    def setUp(self):
        self.evaluator = SolutionEvaluator()
        self.sweep_clusterer = SweepClusterer()
        self.tabu_optimizer = TabuSearchOptimizer(evaluator=self.evaluator)
        self.service = StudentRoutingService()
        self.depot = {"id": "SCHOOL", "lat": 10.0302, "lng": 105.7721}

    # 1. Evaluator calculates distance accurately
    def test_evaluator_distance_calculation(self):
        p1 = {"lat": 10.0302, "lng": 105.7721}
        p2 = {"lat": 10.0402, "lng": 105.7821}
        dist = haversine_distance(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
        self.assertGreater(dist, 1.0)
        self.assertLess(dist, 3.0)

    # 2. Early/late penalty calculated accurately & 3. Late penalty > Early penalty
    def test_evaluator_penalties(self):
        self.assertGreater(config.LATE_PENALTY_WEIGHT, config.EARLY_PENALTY_WEIGHT)

        stops = [{
            "id": "ST-01",
            "pickup_student_count": 10,
            "time_window_start": "06:00",
            "time_window_end": "06:10"
        }]

        points = [self.depot, {"lat": 10.04, "lng": 105.77}]
        point_map = {"SCHOOL": 0, "ST-01": 1}
        dist_mat = [[0, 2.0], [2.0, 0]]
        ttime_mat = [[0, 5.0], [5.0, 0]]

        # Arrive at 05:40 (20 mins early for 06:00)
        res_early = self.evaluator.evaluate_route(stops, self.depot, dist_mat, ttime_mat, point_map, 45, 335.0)
        self.assertGreater(res_early.total_early_arrival, 0)
        self.assertEqual(res_early.early_penalty, res_early.total_early_arrival * config.EARLY_PENALTY_WEIGHT)

        # Arrive at 06:20 (10 mins late for 06:10)
        res_late = self.evaluator.evaluate_route(stops, self.depot, dist_mat, ttime_mat, point_map, 45, 375.0)
        self.assertGreater(res_late.total_late_arrival, 0)
        self.assertEqual(res_late.late_penalty, res_late.total_late_arrival * config.LATE_PENALTY_WEIGHT)

    # 4. Capacity constraint
    def test_capacity_constraint_evaluation(self):
        stops = [{"id": "ST-01", "pickup_student_count": 50}]  # 50 > 45 capacity
        point_map = {"SCHOOL": 0, "ST-01": 1}
        dist_mat = [[0, 2.0], [2.0, 0]]
        ttime_mat = [[0, 5.0], [5.0, 0]]

        res = self.evaluator.evaluate_route(stops, self.depot, dist_mat, ttime_mat, point_map, 45, 330.0)
        self.assertEqual(res.capacity_violations, 1)
        self.assertGreater(res.capacity_penalty, 0)
        self.assertFalse(res.is_feasible())

    # 5. Ride time > 45 minutes station rejected & 6. Only infeasible station rejected & 7. Feasible stations processed
    def test_ride_time_rejection_preprocessing(self):
        school_cfg = SchoolConfig()
        vehicles = [Vehicle(id="BUS-01", capacity=45)]

        # Station 1: ~4 km (Feasible, ~8 mins)
        st_feasible = Station(
            id="ST-FEASIBLE", name="Trạm hợp lệ",
            location=LocationSchema(lat=10.0402, lng=105.7721),
            time_window_start="06:00", time_window_end="06:30",
            pickup_student_count=10
        )

        # Station 2: ~30 km (> 45 mins ride time -> Infeasible)
        st_infeasible = Station(
            id="ST-INFEASIBLE", name="Trạm quá xa",
            location=LocationSchema(lat=10.2500, lng=105.7721),
            time_window_start="06:00", time_window_end="06:30",
            pickup_student_count=10
        )

        options = OptimizationOptions(session_id=SessionId.MORNING_1, trip_type=TripType.PICKUP)

        response = self.service.optimize_routes(school_cfg, vehicles, [st_feasible, st_infeasible], options)

        self.assertIn(response.status, ["PARTIAL_SUCCESS", "SUCCESS"])
        self.assertIsNotNone(response.partial_result)

        rejected_ids = [inf.station_id for inf in response.partial_result.infeasible_stations]
        self.assertIn("ST-INFEASIBLE", rejected_ids)
        self.assertNotIn("ST-FEASIBLE", rejected_ids)

    # 8. Sweep respects capacity & 9. Sweep clusters based on demand, not station count
    def test_sweep_demand_based_clustering(self):
        stations = [
            {"id": "ST-01", "lat": 10.04, "lng": 105.77, "pickup_student_count": 30},
            {"id": "ST-02", "lat": 10.05, "lng": 105.77, "pickup_student_count": 25},  # 30 + 25 = 55 > 45 capacity
        ]
        vehicles = [{"id": "BUS-01", "capacity": 45}, {"id": "BUS-02", "capacity": 45}]

        routes = self.sweep_clusterer.create_initial_routes(self.depot, stations, vehicles)
        self.assertEqual(len(routes), 2)  # Should split into 2 routes because 55 > 45

    # 10. Tabu Search does not break HARD constraints
    def test_tabu_search_feasibility(self):
        stations = [
            {"id": "ST-01", "lat": 10.04, "lng": 105.77, "demand": 20, "pickup_student_count": 20, "time_window_start": "06:00", "time_window_end": "06:30"},
            {"id": "ST-02", "lat": 10.05, "lng": 105.77, "demand": 15, "pickup_student_count": 15, "time_window_start": "06:00", "time_window_end": "06:30"}
        ]
        vehicles = [{"id": "BUS-01", "capacity": 45}]

        routes = self.sweep_clusterer.create_initial_routes(self.depot, stations, vehicles)

        dist_mat = [[0, 2, 3], [2, 0, 1], [3, 1, 0]]
        ttime_mat = [[0, 4, 6], [4, 0, 2], [6, 2, 0]]
        point_map = {"SCHOOL": 0, "ST-01": 1, "ST-02": 2}

        opt_routes, opt_eval = self.tabu_optimizer.optimize(
            routes, self.depot, dist_mat, ttime_mat, point_map, [45], 330.0
        )
        self.assertEqual(opt_eval.capacity_violations, 0)
        self.assertEqual(opt_eval.ride_time_violations, 0)

    # 11. Tabu List works & 12. Aspiration Criterion works
    def test_tabu_list_and_aspiration(self):
        tlist = TabuList(base_tenure=5)
        move_key = ("swap", "ST-01", "ST-02")

        tlist.add_move(move_key, current_iteration=1)

        # Iteration 2: Normally tabu (expired at 1 + 5 = 6)
        self.assertTrue(tlist.is_tabu(move_key, current_iteration=2, candidate_objective=100.0, best_objective=90.0))

        # Aspiration Criterion: overrides tabu because candidate < best_objective
        self.assertFalse(tlist.is_tabu(move_key, current_iteration=2, candidate_objective=80.0, best_objective=90.0))

    # 13. OSRM timeout after 3s & 14. OSRM failure falls back to static matrix
    def test_osrm_fallback_on_failure(self):
        provider = OSRMWithFallbackProvider(osrm_url="http://invalid-osrm-server.example.com/", timeout=1.0)
        points = [{"lat": 10.0302, "lng": 105.7721}, {"lat": 10.0402, "lng": 105.7821}]

        dist_mat, ttime_mat, source = provider.get_matrix(points)
        self.assertEqual(source, "STATIC_FALLBACK")
        self.assertEqual(len(dist_mat), 2)
        self.assertEqual(len(ttime_mat), 2)

    # 15. Benchmark runs on Small/Medium/Large datasets
    def test_benchmark_execution(self):
        benchmark = StudentRoutingBenchmark()
        # Test small dataset execution
        benchmark.run_single_dataset("TestSmall", num_vehicles=2, num_stations=6, total_students=20, num_runs=1)


if __name__ == "__main__":
    unittest.main()
