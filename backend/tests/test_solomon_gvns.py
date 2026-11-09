from pathlib import Path
from random import Random

from app.services.student_routing.solomon.benchmark_runner import _resolve_raw_instance
from app.services.student_routing.solomon.gvns_benchmark_runner import run_instance
from app.services.student_routing.solomon.gvns_optimizer import (
    GVNSConfig, SolomonGVNSOptimizer, _moves, apply_move, guided_score,
)
from app.services.student_routing.solomon.reverse_pickup_evaluator import ReversePickupEvaluator
from app.services.student_routing.solomon.reverse_pickup_sweep import ReversePickupSweep
from app.services.student_routing.solomon.reverse_pickup_transformer import transform_reverse_pickup
from app.services.student_routing.solomon.solomon_parser import parse_solomon_instance

BACKEND_ROOT = Path(__file__).resolve().parents[1]
RAW_C101 = BACKEND_ROOT / "datasets/solomon/raw/In/c101.txt"


def _initial(name="C101"):
    raw = _resolve_raw_instance(BACKEND_ROOT, name)
    evaluator = ReversePickupEvaluator(transform_reverse_pickup(parse_solomon_instance(raw)))
    return evaluator, ReversePickupSweep(evaluator).create_initial_routes()


def test_moves_and_shaking_keep_every_station_once():
    evaluator, initial = _initial()
    expected = sorted(station["id"] for route in initial for station in route)
    for kind in ("2opt", "swap", "relocate"):
        moves = _moves(initial, kind)
        assert moves
        candidate = apply_move(initial, kind, Random(100).choice(moves))
        assert sorted(station["id"] for route in candidate for station in route) == expected
    optimizer = SolomonGVNSOptimizer(evaluator, GVNSConfig(), Random(100))
    for level in range(3):
        shaken = optimizer._shaking(initial, level, set(expected))
        assert sorted(station["id"] for route in shaken for station in route) == expected


def test_guided_score_prefers_feasible_then_fewer_violations():
    feasible = {"is_feasible": True, "fleet_violations": 0, "capacity_violations": 0,
                "time_window_violations": 0, "depot_window_violations": 0,
                "vehicles_used": 20, "total_distance": 999.0}
    slight = {**feasible, "is_feasible": False, "time_window_violations": 1,
              "vehicles_used": 1, "total_distance": 1.0}
    severe = {**slight, "time_window_violations": 3, "total_distance": 0.0}
    assert guided_score(feasible) < guided_score(slight) < guided_score(severe)


def test_gvns_c101_c201_output_is_complete_and_reproducible():
    before = RAW_C101.read_bytes()
    for name in ("C101", "C201"):
        result = run_instance(name, seed=100, max_iterations=2, max_runtime_seconds=30,
                              candidates_per_neighborhood=30, backend_root=BACKEND_ROOT)
        ids = [stop["source_customer_id"] for route in result["routes"] for stop in route["stops"]]
        assert sorted(ids) == list(range(1, 101))
        assert len(ids) == len(set(ids))
        assert result["budget"]["iterations_completed"] == 2
        assert set(result["gvns_diagnostics"]["vnd_neighborhoods"]) == {"2opt", "swap", "relocate"}
        assert set(result["gvns_diagnostics"]["shaking_neighborhoods"]) == {"relocate_1", "swap_1", "relocate_2_3"}
        if result["is_feasible"]:
            assert result["capacity_violations"] == result["time_window_violations"] == 0
            assert result["depot_window_violations"] == result["fleet_violations"] == 0
    first = run_instance("C201", seed=101, max_iterations=2, max_runtime_seconds=30,
                         candidates_per_neighborhood=30, backend_root=BACKEND_ROOT)
    second = run_instance("C201", seed=101, max_iterations=2, max_runtime_seconds=30,
                          candidates_per_neighborhood=30, backend_root=BACKEND_ROOT)
    assert first["total_distance"] == second["total_distance"]
    assert [[stop["id"] for stop in route["stops"]] for route in first["routes"]] == [
        [stop["id"] for stop in route["stops"]] for route in second["routes"]]
    assert RAW_C101.read_bytes() == before
