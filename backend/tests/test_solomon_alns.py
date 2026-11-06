import json
from pathlib import Path

from app.services.student_routing.solomon.alns_benchmark_runner import run_instance


BACKEND_ROOT = Path(__file__).resolve().parents[1]
RAW_C101 = BACKEND_ROOT / "datasets/solomon/raw/In/c101.txt"


def _station_ids(result):
    return [stop["source_customer_id"] for route in result["routes"] for stop in route["stops"]]


def test_alns_c101_writes_complete_valid_result():
    before = RAW_C101.read_bytes()
    result = run_instance("C101", seed=100, max_iterations=15, max_runtime_seconds=30, backend_root=BACKEND_ROOT)
    output = BACKEND_ROOT / "evidence/solomon/C101/sweep_alns_seed_100.json"
    persisted = json.loads(output.read_text(encoding="utf-8"))
    required = {"instance", "algorithm", "seed", "is_feasible", "vehicles_used", "total_distance", "runtime_seconds", "budget", "initial_sweep", "operator_statistics", "routes"}
    assert required <= result.keys()
    assert persisted["algorithm"] == "sweep_alns"
    assert sorted(_station_ids(result)) == list(range(1, 101))
    assert len(_station_ids(result)) == len(set(_station_ids(result)))
    assert all(route["stops"] for route in result["routes"])
    assert set(result["operator_statistics"]["destroy"]) == {"random_removal", "worst_removal", "related_removal", "route_removal"}
    assert set(result["operator_statistics"]["repair"]) == {"greedy_insertion", "regret_2_insertion"}
    assert sum(item["usage_count"] for item in result["operator_statistics"]["destroy"].values()) == result["budget"]["iterations_completed"]
    assert sum(item["usage_count"] for item in result["operator_statistics"]["repair"].values()) == result["budget"]["iterations_completed"]
    assert RAW_C101.read_bytes() == before
    if result["is_feasible"]:
        assert result["capacity_violations"] == result["time_window_violations"] == 0
        assert result["depot_window_violations"] == result["fleet_violations"] == 0


def test_alns_is_reproducible_and_supports_non_c101_instance():
    first = run_instance("C201", seed=101, max_iterations=10, max_runtime_seconds=30, backend_root=BACKEND_ROOT)
    second = run_instance("C201", seed=101, max_iterations=10, max_runtime_seconds=30, backend_root=BACKEND_ROOT)
    assert first["total_distance"] == second["total_distance"]
    assert first["vehicles_used"] == second["vehicles_used"]
    assert [[stop["id"] for stop in route["stops"]] for route in first["routes"]] == [[stop["id"] for stop in route["stops"]] for route in second["routes"]]
