import json
from pathlib import Path

import pytest

from app.services.student_routing.solomon.benchmark_runner import run_c101, run_instance
from app.services.student_routing.solomon.reverse_pickup_evaluator import ReversePickupEvaluator
from app.services.student_routing.solomon.reverse_pickup_transformer import transform_reverse_pickup
from app.services.student_routing.solomon.solomon_parser import parse_solomon_instance


BACKEND_ROOT = Path(__file__).resolve().parents[1]
RAW_C101 = BACKEND_ROOT / "datasets/solomon/raw/In/c101.txt"


def test_parser_reads_c101_depot_and_100_customers():
    instance = parse_solomon_instance(RAW_C101)
    assert instance.name == "C101"
    assert instance.depot.customer_id == 0
    assert instance.depot.due_date == 1236
    assert len(instance.customers) == 100


def test_customer_one_window_is_reversed_as_specified():
    transformed = transform_reverse_pickup(parse_solomon_instance(RAW_C101))
    customer_one = transformed["stations"][0]
    assert customer_one["source_time_window_start"] == 912
    assert customer_one["source_time_window_end"] == 967
    assert customer_one["service_time"] == 90
    assert [customer_one["time_window_start"], customer_one["time_window_end"]] == [179, 234]


def test_transformed_data_has_metadata_and_all_stations_without_mutating_raw():
    before = RAW_C101.read_bytes()
    transformed = transform_reverse_pickup(parse_solomon_instance(RAW_C101))
    assert RAW_C101.read_bytes() == before
    assert transformed["dataset_type"] == "solomon_reverse_pickup"
    assert transformed["transform"]["planning_horizon"] == 1236
    assert len(transformed["stations"]) == 100


def test_euclidean_matrix_is_symmetric_with_zero_diagonal():
    evaluator = ReversePickupEvaluator(transform_reverse_pickup(parse_solomon_instance(RAW_C101)))
    for row_index, row in enumerate(evaluator.matrix):
        assert row[row_index] == 0.0
        for column_index, value in enumerate(row):
            assert value == pytest.approx(evaluator.matrix[column_index][row_index])


def test_sweep_tabu_benchmark_writes_valid_complete_result():
    result = run_c101(seed=100, max_runtime_seconds=0.2, backend_root=BACKEND_ROOT)
    output = BACKEND_ROOT / "evidence/solomon/C101/sweep_tabu_budget_0.2s_seed_100.json"
    persisted = json.loads(output.read_text(encoding="utf-8"))
    ids = [stop["source_customer_id"] for route in result["routes"] for stop in route["stops"]]
    assert persisted["seed"] == 100
    assert result["algorithm"] == "sweep_tabu"
    assert result["budget"]["max_runtime_seconds"] == 0.2
    assert result["initial_sweep"]["total_distance"] > 0
    assert sorted(ids) == list(range(1, 101))
    assert len(ids) == len(set(ids))
    if result["is_feasible"]:
        assert result["capacity_violations"] == 0
        assert result["time_window_violations"] == 0
        assert result["depot_window_violations"] == 0
        assert result["fleet_violations"] == 0


def test_runner_accepts_instance_name_and_writes_seed_specific_output():
    result = run_instance("c101", seed=101, max_runtime_seconds=0.2, backend_root=BACKEND_ROOT)
    output = BACKEND_ROOT / "evidence/solomon/C101/sweep_tabu_budget_0.2s_seed_101.json"
    assert result["instance"] == "C101_reverse_pickup"
    assert result["seed"] == 101
    assert output.exists()
