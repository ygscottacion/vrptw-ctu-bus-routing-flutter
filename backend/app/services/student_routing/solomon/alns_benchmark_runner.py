"""CLI runner for the isolated Solomon Reverse-Pickup Sweep + ALNS benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from random import Random
from time import perf_counter
from typing import Any

from .alns_optimizer import ALNSConfig, SolomonALNSOptimizer
from .benchmark_runner import _resolve_raw_instance
from .reverse_pickup_evaluator import ReversePickupEvaluator
from .reverse_pickup_sweep import ReversePickupSweep
from .reverse_pickup_transformer import write_reverse_pickup
from .solomon_parser import parse_solomon_instance


def _serialize_result(instance_name: str, seed: int, evaluation: dict[str, Any], runtime: float,
                      budget: dict[str, Any], initial: dict[str, Any], evaluator: ReversePickupEvaluator,
                      transformed: dict[str, Any]) -> dict[str, Any]:
    return {
        "instance": f"{instance_name}_reverse_pickup", "algorithm": "sweep_alns", "seed": seed,
        "is_feasible": evaluation["is_feasible"], "vehicles_used": evaluation["vehicles_used"],
        "total_distance": round(evaluation["total_distance"], 6),
        "total_travel_time": round(evaluation["total_travel_time"], 6),
        "total_service_time": round(evaluation["total_service_time"], 6),
        "capacity_violations": evaluation["capacity_violations"],
        "time_window_violations": evaluation["time_window_violations"],
        "depot_window_violations": evaluation["depot_window_violations"],
        "fleet_violations": evaluation["fleet_violations"], "runtime_seconds": round(runtime, 6),
        "budget": {key: budget[key] for key in ("max_iterations", "max_runtime_seconds", "iterations_completed", "evaluations_completed", "stop_reason")},
        "initial_sweep": {key: initial[key] for key in ("is_feasible", "vehicles_used", "total_distance")},
        "operator_statistics": {"destroy": budget["destroy"], "repair": budget["repair"]},
        "routes": [
            {
                "vehicle_index": index + 1, "capacity": evaluator.capacity,
                "total_demand": route_eval.total_demand, "route_distance": round(route_eval.route_distance, 6),
                "departure_time": transformed["depot"]["time_window_start"], "return_time": round(route_eval.return_time, 6),
                "stops": route_eval.stops,
            }
            for index, route_eval in enumerate(evaluation["route_evaluations"])
        ],
    }


def run_instance(instance_name: str = "C101", seed: int = 100, max_iterations: int = 10_000,
                 max_runtime_seconds: float = 5.0, backend_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(backend_root) if backend_root else Path(__file__).resolve().parents[4]
    normalized = instance_name.upper()
    instance = parse_solomon_instance(_resolve_raw_instance(root, normalized))
    if instance.name != normalized:
        raise ValueError(f"Requested {normalized}, but input file contains {instance.name}")
    transformed = write_reverse_pickup(instance, root / f"datasets/solomon/reverse_pickup/{normalized}_reverse_pickup.json")
    evaluator = ReversePickupEvaluator(transformed)
    initial = evaluator.evaluate_solution(ReversePickupSweep(evaluator).create_initial_routes())
    optimizer = SolomonALNSOptimizer(
        evaluator, ALNSConfig(max_iterations=max_iterations, max_runtime_seconds=max_runtime_seconds), Random(seed)
    )
    started = perf_counter()
    _, evaluation, budget = optimizer.optimize(ReversePickupSweep(evaluator).create_initial_routes(), perf_counter)
    result = _serialize_result(normalized, seed, evaluation, perf_counter() - started, budget, initial, evaluator, transformed)
    output = root / f"evidence/solomon/{normalized}/sweep_alns_seed_{seed}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Solomon Reverse-Pickup Sweep + ALNS benchmark.")
    parser.add_argument("--instance", default="C101")
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--max-iterations", type=int, default=10_000)
    parser.add_argument("--max-runtime-seconds", type=float, default=5.0)
    arguments = parser.parse_args()
    print(json.dumps(run_instance(arguments.instance, arguments.seed, arguments.max_iterations,
                                  arguments.max_runtime_seconds), indent=2, ensure_ascii=False))
