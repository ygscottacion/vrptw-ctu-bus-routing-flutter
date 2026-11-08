"""CLI runner for isolated Solomon Reverse-Pickup Sweep + GVNS."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from random import Random
from time import perf_counter
from typing import Any
from .benchmark_runner import _resolve_raw_instance
from .gvns_optimizer import GVNSConfig, SolomonGVNSOptimizer
from .reverse_pickup_evaluator import ReversePickupEvaluator
from .reverse_pickup_sweep import ReversePickupSweep
from .reverse_pickup_transformer import write_reverse_pickup
from .solomon_parser import parse_solomon_instance


def run_instance(instance_name: str = "C101", seed: int = 100, max_iterations: int = 10_000,
                 max_runtime_seconds: float = 5.0, candidates_per_neighborhood: int = 500,
                 backend_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(backend_root) if backend_root else Path(__file__).resolve().parents[4]
    name = instance_name.upper()
    instance = parse_solomon_instance(_resolve_raw_instance(root, name))
    transformed = write_reverse_pickup(instance, root / f"datasets/solomon/reverse_pickup/{name}_reverse_pickup.json")
    evaluator = ReversePickupEvaluator(transformed)
    sweep = ReversePickupSweep(evaluator).create_initial_routes()
    initial = evaluator.evaluate_solution(sweep)
    started = perf_counter()
    routes, evaluation, budget = SolomonGVNSOptimizer(
        evaluator, GVNSConfig(max_iterations, max_runtime_seconds, candidates_per_neighborhood), Random(seed)
    ).optimize(sweep)
    result: dict[str, Any] = {"instance": f"{name}_reverse_pickup", "algorithm": "sweep_gvns", "seed": seed,
        "is_feasible": evaluation["is_feasible"], "vehicles_used": evaluation["vehicles_used"],
        "total_distance": round(evaluation["total_distance"], 6), "total_travel_time": round(evaluation["total_travel_time"], 6),
        "total_service_time": round(evaluation["total_service_time"], 6), "capacity_violations": evaluation["capacity_violations"],
        "time_window_violations": evaluation["time_window_violations"], "depot_window_violations": evaluation["depot_window_violations"],
        "fleet_violations": evaluation["fleet_violations"], "runtime_seconds": round(perf_counter() - started, 6),
        "initial_sweep": {key: initial[key] for key in ("is_feasible", "vehicles_used", "total_distance")},
        "budget": {key: budget[key] for key in ("max_iterations", "max_runtime_seconds", "iterations_completed", "evaluations_completed", "stop_reason")},
        "gvns_diagnostics": budget["gvns_diagnostics"], "routes": [{"vehicle_index": index + 1, "capacity": evaluator.capacity,
            "total_demand": route_eval.total_demand, "route_distance": round(route_eval.route_distance, 6),
            "departure_time": transformed["depot"]["time_window_start"], "return_time": round(route_eval.return_time, 6), "stops": route_eval.stops}
            for index, route_eval in enumerate(evaluation["route_evaluations"])]}
    output = root / f"evidence/solomon/{name}/sweep_gvns_seed_{seed}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Solomon Reverse-Pickup Sweep + GVNS.")
    parser.add_argument("--instance", default="C101"); parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--max-iterations", type=int, default=10_000); parser.add_argument("--max-runtime-seconds", type=float, default=5.0)
    parser.add_argument("--candidates-per-neighborhood", type=int, default=500)
    args = parser.parse_args()
    print(json.dumps(run_instance(args.instance, args.seed, args.max_iterations, args.max_runtime_seconds,
                                  args.candidates_per_neighborhood), indent=2, ensure_ascii=False))
