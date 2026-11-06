from pathlib import Path
from random import Random

from app.services.student_routing.solomon.benchmark_runner import _resolve_raw_instance
from app.services.student_routing.solomon.reverse_pickup_evaluator import ReversePickupEvaluator
from app.services.student_routing.solomon.reverse_pickup_sweep import ReversePickupSweep
from app.services.student_routing.solomon.reverse_pickup_transformer import transform_reverse_pickup
from app.services.student_routing.solomon.solomon_parser import parse_solomon_instance
from app.services.student_routing.solomon.tabu_v2_benchmark_runner import run_instance
from app.services.student_routing.solomon.tabu_v2_optimizer import _all_moves, _apply_move, guided_score


BACKEND_ROOT = Path(__file__).resolve().parents[1]
RAW_C101 = BACKEND_ROOT / "datasets/solomon/raw/In/c101.txt"


def _ids(solution):
    return [station["source_customer_id"] for route in solution for station in route]


def test_tabu_v2_moves_cover_all_types_and_preserve_stations():
    evaluator = ReversePickupEvaluator(transform_reverse_pickup(parse_solomon_instance(RAW_C101)))
    initial = ReversePickupSweep(evaluator).create_initial_routes()
    moves = _all_moves(initial)
    assert {move[0] for move in moves} == {"2opt", "swap", "relocate"}
    expected = sorted(_ids(initial))
    for move in Random(100).sample(moves, min(60, len(moves))):
        assert sorted(_ids(_apply_move(initial, move))) == expected


def test_guided_score_prefers_feasibility_then_fewer_violations():
    feasible = {"is_feasible": True, "fleet_violations": 0, "capacity_violations": 0,
                "time_window_violations": 0, "depot_window_violations": 0,
                "vehicles_used": 20, "total_distance": 9999.0}
    slight_violation = {**feasible, "is_feasible": False, "time_window_violations": 1,
                        "vehicles_used": 1, "total_distance": 1.0}
    severe_violation = {**slight_violation, "time_window_violations": 3, "total_distance": 0.0}
    assert guided_score(feasible) < guided_score(slight_violation) < guided_score(severe_violation)


def test_c201_sweep_has_a_feasible_improving_one_move():
    """Guard against falsely concluding that C201's Sweep is a local optimum."""
    raw = BACKEND_ROOT / "datasets/solomon/raw/In/c201.txt"
    evaluator = ReversePickupEvaluator(transform_reverse_pickup(parse_solomon_instance(raw)))
    sweep = ReversePickupSweep(evaluator).create_initial_routes()
    baseline = evaluator.evaluate_solution(sweep)
    known_improving_swap = next(
        move for move in _all_moves(sweep)
        if move == ("swap", (0, 5, 2, 6, "customer_50", "customer_73"))
    )
    candidate = evaluator.evaluate_solution(_apply_move(sweep, known_improving_swap))
    assert candidate["is_feasible"]
    assert candidate["total_distance"] < baseline["total_distance"]


def test_tabu_v2_runs_c101_and_c201_and_is_deterministic_by_iterations():
    before = RAW_C101.read_bytes()
    for name in ("C101", "C201"):
        result = run_instance(name, seed=100, max_iterations=2, max_runtime_seconds=30, backend_root=BACKEND_ROOT)
        ids = [stop["source_customer_id"] for route in result["routes"] for stop in route["stops"]]
        assert sorted(ids) == list(range(1, 101))
        assert len(ids) == len(set(ids))
        assert result["tabu_diagnostics"]["candidate_counts"]
        assert result["budget"]["iterations_completed"] == 2
        if result["is_feasible"]:
            assert result["capacity_violations"] == result["time_window_violations"] == 0
            assert result["depot_window_violations"] == result["fleet_violations"] == 0
    first = run_instance("C201", seed=101, max_iterations=2, max_runtime_seconds=30, backend_root=BACKEND_ROOT)
    second = run_instance("C201", seed=101, max_iterations=2, max_runtime_seconds=30, backend_root=BACKEND_ROOT)
    assert first["total_distance"] == second["total_distance"]
    assert [[stop["id"] for stop in route["stops"]] for route in first["routes"]] == [
        [stop["id"] for stop in route["stops"]] for route in second["routes"]
    ]
    assert RAW_C101.read_bytes() == before
