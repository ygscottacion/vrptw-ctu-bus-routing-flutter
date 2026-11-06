"""Runnable Solomon Reverse-Pickup benchmark: Sweep construction followed by Tabu search."""
from __future__ import annotations

import argparse
import copy
import json
import random
import time
from pathlib import Path
from typing import Any

from .reverse_pickup_evaluator import ReversePickupEvaluator
from .reverse_pickup_sweep import ReversePickupSweep
from .reverse_pickup_transformer import write_reverse_pickup
from .solomon_parser import parse_solomon_instance


def _score(evaluation: dict[str, Any]) -> tuple[int, int, float]:
    """Lexicographic objective: feasibility, vehicle count, distance."""
    return (0 if evaluation["is_feasible"] else 1, evaluation["vehicles_used"], evaluation["total_distance"])


def _signature(routes: list[list[dict[str, Any]]]) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(stop["id"] for stop in route) for route in routes)


def _neighborhood(routes: list[list[dict[str, Any]]], rng: random.Random,
                  limit: int = 90) -> list[list[list[dict[str, Any]]]]:
    """Sample a balanced, seed-reproducible Tabu neighbourhood.

    The former implementation returned the first 80 enumerated 2-opt moves.
    On a 100-station instance, that could prevent relocate moves from ever
    being examined.  Sampling 2-opt, relocate and swap moves in equal turns
    gives every standard Tabu move type a chance under the same time budget.
    """
    candidates: list[list[list[dict[str, Any]]]] = []
    seen: set[tuple[tuple[str, ...], ...]] = set()
    non_empty_routes = [index for index, route in enumerate(routes) if route]
    two_opt_routes = [index for index, route in enumerate(routes) if len(route) >= 2]
    positions = [(route_index, stop_index) for route_index, route in enumerate(routes)
                 for stop_index in range(len(route))]
    move_types = ("two_opt", "relocate", "swap")
    attempts = 0

    while len(candidates) < limit and attempts < limit * 30:
        move_type = move_types[attempts % len(move_types)]
        attempts += 1
        candidate: list[list[dict[str, Any]]] | None = None

        if move_type == "two_opt" and two_opt_routes:
            route_index = rng.choice(two_opt_routes)
            left, right = sorted(rng.sample(range(len(routes[route_index])), 2))
            candidate = copy.deepcopy(routes)
            candidate[route_index][left:right + 1] = reversed(candidate[route_index][left:right + 1])

        elif move_type == "relocate" and non_empty_routes:
            source = rng.choice(non_empty_routes)
            item_index = rng.randrange(len(routes[source]))
            target = rng.choice(non_empty_routes)
            position = rng.randrange(len(routes[target]) + 1)
            if source != target or position not in (item_index, item_index + 1):
                candidate = copy.deepcopy(routes)
                item = candidate[source].pop(item_index)
                insert_at = position if source != target or position < item_index else position - 1
                candidate[target].insert(insert_at, item)
                candidate = [route for route in candidate if route]

        elif move_type == "swap" and len(positions) >= 2:
            (first_route, first_stop), (second_route, second_stop) = rng.sample(positions, 2)
            candidate = copy.deepcopy(routes)
            candidate[first_route][first_stop], candidate[second_route][second_stop] = (
                candidate[second_route][second_stop], candidate[first_route][first_stop]
            )

        if candidate is not None:
            signature = _signature(candidate)
            if signature not in seen:
                seen.add(signature)
                candidates.append(candidate)
    return candidates


def tabu_optimize(initial_routes: list[list[dict[str, Any]]], evaluator: ReversePickupEvaluator,
                  max_iterations: int = 10_000, tenure: int = 10,
                  max_runtime_seconds: float = 5.0,
                  early_stopping_rounds: int | None = None,
                  seed: int = 100) -> tuple[list[list[dict[str, Any]]], dict[str, Any], dict[str, int | float | str | None]]:
    """Run the benchmark Tabu search with the same wall-clock budget as ALNS.

    This is deliberately isolated from the CTU production optimizer.  It keeps
    this benchmark's existing 2-opt and inter-route relocate neighborhoods,
    while stopping on a common time budget instead of the former 50-iteration
    cap.  Early stopping is disabled by default so it consumes the same
    wall-clock budget supplied to ALNS; this does not affect production Tabu.
    """
    current = copy.deepcopy(initial_routes)
    best = copy.deepcopy(initial_routes)
    best_eval = evaluator.evaluate_solution(best)
    tabu: dict[tuple[tuple[str, ...], ...], int] = {}
    rng = random.Random(seed)
    stale = 0
    started = time.perf_counter()
    iterations_completed = 0
    evaluations_completed = 1
    stop_reason = "max_iterations"
    for iteration in range(max_iterations):
        if time.perf_counter() - started >= max_runtime_seconds:
            stop_reason = "time_limit"
            break
        candidates = _neighborhood(current, rng)
        ranked: list[tuple[tuple[int, int, float], list[list[dict[str, Any]]], dict[str, Any]]] = []
        deadline_reached = False
        for candidate in candidates:
            if time.perf_counter() - started >= max_runtime_seconds:
                deadline_reached = True
                break
            evaluation = evaluator.evaluate_solution(candidate)
            evaluations_completed += 1
            signature = _signature(candidate)
            if tabu.get(signature, -1) > iteration and _score(evaluation) >= _score(best_eval):
                continue
            ranked.append((_score(evaluation), candidate, evaluation))
        if not ranked:
            stop_reason = "time_limit" if deadline_reached else "no_candidates"
            break
        _, current, current_eval = min(ranked, key=lambda item: item[0])
        signature = _signature(current)
        tabu[signature] = iteration + tenure
        if _score(current_eval) < _score(best_eval):
            best, best_eval, stale = copy.deepcopy(current), current_eval, 0
        else:
            stale += 1
        iterations_completed += 1
        if early_stopping_rounds is not None and stale >= early_stopping_rounds:
            stop_reason = "early_stopping"
            break
    return best, best_eval, {
        "max_iterations": max_iterations,
        "max_runtime_seconds": max_runtime_seconds,
        "iterations_completed": iterations_completed,
        "evaluations_completed": evaluations_completed,
        "early_stopping_rounds": early_stopping_rounds,
        "neighborhoods": ["2-opt", "relocate", "swap"],
        "candidates_per_iteration": 90,
        "stop_reason": stop_reason,
    }


def _resolve_raw_instance(backend_root: Path, instance_name: str) -> Path:
    """Locate an instance in either documented raw layout without moving raw data."""
    normalized = instance_name.upper()
    for candidate in (
        backend_root / f"datasets/solomon/raw/{normalized}.txt",
        backend_root / f"datasets/solomon/raw/{normalized.lower()}.txt",
        backend_root / f"datasets/solomon/raw/In/{normalized}.txt",
        backend_root / f"datasets/solomon/raw/In/{normalized.lower()}.txt",
    ):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not find {normalized}.txt in datasets/solomon/raw or datasets/solomon/raw/In"
    )


def run_instance(instance_name: str = "C101", seed: int = 100, max_iterations: int = 10_000,
                 max_runtime_seconds: float = 5.0, early_stopping_rounds: int | None = None,
                 backend_root: str | Path | None = None) -> dict[str, Any]:
    """Run one named Solomon instance with a configurable Tabu time budget."""
    root = Path(backend_root) if backend_root else Path(__file__).resolve().parents[4]
    normalized = instance_name.upper()
    raw_path = _resolve_raw_instance(root, normalized)
    instance = parse_solomon_instance(raw_path)
    if instance.name != normalized:
        raise ValueError(f"Requested {normalized}, but input file contains {instance.name}")
    transformed_path = root / f"datasets/solomon/reverse_pickup/{normalized}_reverse_pickup.json"
    transformed = write_reverse_pickup(instance, transformed_path)
    random.seed(seed)
    evaluator = ReversePickupEvaluator(transformed)
    sweep_routes = ReversePickupSweep(evaluator).create_initial_routes()
    initial_sweep = evaluator.evaluate_solution(sweep_routes)
    started = time.perf_counter()
    routes, evaluation, budget = tabu_optimize(
        sweep_routes, evaluator, max_iterations=max_iterations,
        max_runtime_seconds=max_runtime_seconds, early_stopping_rounds=early_stopping_rounds, seed=seed,
    )
    runtime = time.perf_counter() - started
    result = {
        "instance": f"{normalized}_reverse_pickup", "algorithm": "sweep_tabu", "seed": seed,
        "is_feasible": evaluation["is_feasible"], "vehicles_used": evaluation["vehicles_used"],
        "total_distance": round(evaluation["total_distance"], 6),
        "total_travel_time": round(evaluation["total_travel_time"], 6),
        "total_service_time": round(evaluation["total_service_time"], 6),
        "capacity_violations": evaluation["capacity_violations"],
        "time_window_violations": evaluation["time_window_violations"],
        "depot_window_violations": evaluation["depot_window_violations"],
        "fleet_violations": evaluation["fleet_violations"],
        "runtime_seconds": round(runtime, 6),
        "budget": budget,
        "initial_sweep": {
            "is_feasible": initial_sweep["is_feasible"],
            "vehicles_used": initial_sweep["vehicles_used"],
            "total_distance": initial_sweep["total_distance"],
        },
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
    budget_label = f"{max_runtime_seconds:g}"
    result_path = root / f"evidence/solomon/{normalized}/sweep_tabu_budget_{budget_label}s_seed_{seed}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def run_c101(seed: int = 100, max_iterations: int = 10_000, max_runtime_seconds: float = 5.0,
             early_stopping_rounds: int | None = None, backend_root: str | Path | None = None) -> dict[str, Any]:
    """Backward-compatible helper for existing C101 tests and callers."""
    return run_instance("C101", seed=seed, max_iterations=max_iterations,
                        max_runtime_seconds=max_runtime_seconds, early_stopping_rounds=early_stopping_rounds,
                        backend_root=backend_root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Solomon Reverse-Pickup Sweep + Tabu benchmark.")
    parser.add_argument("--instance", default="C101", help="Solomon instance name, for example C101 or C201.")
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--max-iterations", type=int, default=10_000)
    parser.add_argument("--max-runtime-seconds", type=float, default=5.0)
    parser.add_argument("--early-stopping-rounds", type=int, default=None,
                        help="Optional benchmark-only early-stop threshold; omitted means run to the time budget.")
    args = parser.parse_args()
    print(json.dumps(run_instance(args.instance, seed=args.seed, max_iterations=args.max_iterations,
                                  max_runtime_seconds=args.max_runtime_seconds,
                                  early_stopping_rounds=args.early_stopping_rounds), indent=2, ensure_ascii=False))
