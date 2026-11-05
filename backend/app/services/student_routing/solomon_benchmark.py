"""Solomon VRPTW instance adapter and benchmark runner.

This module keeps the Solomon objective and timing rules separate from the
CTU pickup evaluator. Distances and travel times use the instance's Euclidean
coordinates, and each customer's own service time is applied.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.student_routing.core.evaluator import EvaluationResult
from app.services.student_routing.core.sweep_clustering import SweepClusterer
from app.services.student_routing.core.tabu_optimizer import TabuSearchOptimizer


# Detailed C101 solution published alongside SINTEF's benchmark table.
C101_BKS_ROUTES = [
    [81, 78, 76, 71, 70, 73, 77, 79, 80],
    [57, 55, 54, 53, 56, 58, 60, 59],
    [98, 96, 95, 94, 92, 93, 97, 100, 99],
    [32, 33, 31, 35, 37, 38, 39, 36, 34],
    [13, 17, 18, 19, 15, 16, 14, 12],
    [90, 87, 86, 83, 82, 84, 85, 88, 89, 91],
    [43, 42, 41, 40, 44, 46, 45, 48, 51, 50, 52, 49, 47],
    [67, 65, 63, 62, 74, 72, 61, 64, 68, 66, 69],
    [5, 3, 7, 8, 10, 11, 9, 6, 4, 2, 1, 75],
    [20, 24, 25, 27, 29, 30, 28, 26, 23, 22, 21],
]


@dataclass(frozen=True)
class SolomonInstance:
    name: str
    vehicle_count: int
    capacity: int
    depot: dict[str, Any]
    customers: list[dict[str, Any]]
    best_known_vehicles: int | None = None
    best_known_distance: float | None = None


def load_solomon_instance(path: str | Path) -> SolomonInstance:
    """Parse the standard Solomon text file format (depot plus customers)."""
    path = Path(path)
    contents = path.read_text(encoding="utf-8-sig")
    rows: list[tuple[int, float, float, int, int, int, int]] = []
    for line in contents.splitlines():
        match = re.fullmatch(
            r"\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*",
            line,
        )
        if match:
            node, x, y, demand, ready, due, service = match.groups()
            rows.append((int(node), float(x), float(y), int(demand), int(ready), int(due), int(service)))

    if len(rows) < 2 or rows[0][0] != 0:
        raise ValueError(f"{path} does not contain a Solomon depot and customer rows")
    vehicle_match = re.search(r"NUMBER\s+CAPACITY\s+(\d+)\s+(\d+)", contents, re.IGNORECASE)
    if not vehicle_match:
        raise ValueError(f"{path} is missing fleet count and capacity")

    fleet, capacity = map(int, vehicle_match.groups())
    depot_row = rows[0]
    depot = {
        "id": "0", "x": depot_row[1], "y": depot_row[2],
        "ready": depot_row[4], "due": depot_row[5], "service": depot_row[6],
    }
    customers = [
        {
            "id": str(node), "x": x, "y": y, "demand": demand,
            "ready": ready, "due": due, "service": service,
        }
        for node, x, y, demand, ready, due, service in rows[1:]
    ]
    return SolomonInstance(path.stem.upper(), fleet, capacity, depot, customers)


class SolomonEvaluator:
    """Feasibility checker and lexicographic Solomon objective adapter."""

    # A violation must always cost more than any possible route-count benefit.
    _VIOLATION_WEIGHT = 1_000_000_000_000.0
    _VEHICLE_WEIGHT = 1_000_000_000.0

    def __init__(self, instance: SolomonInstance):
        self.instance = instance
        self.node_by_id = {node["id"]: node for node in [instance.depot, *instance.customers]}
        self.distance = self._matrix("distance")
        self.travel_time = self._matrix("time")
        self.index = {node["id"]: i for i, node in enumerate([instance.depot, *instance.customers])}

    def _matrix(self, _kind: str) -> list[list[float]]:
        nodes = [self.instance.depot, *self.instance.customers]
        return [
            [math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for b in nodes]
            for a in nodes
        ]

    def evaluate_solution(
        self,
        routes: list[list[dict[str, Any]]],
        depot: dict[str, Any],
        distance_matrix: list[list[float]],
        travel_time_matrix: list[list[float]],
        point_index_map: dict[str, int],
        vehicle_capacities: list[int] | None = None,
        departure_time_mins: float = 0.0,
        arrival_deadline_mins: float | None = None,
        trip_type: str = "PICKUP",
    ) -> EvaluationResult:
        del depot, distance_matrix, travel_time_matrix, point_index_map, arrival_deadline_mins, trip_type
        distances = self.distance
        times = self.travel_time
        cap = self.instance.capacity
        total_distance = total_time = total_lateness = total_early = 0.0
        capacity_violations = time_window_violations = 0

        for route in routes:
            load = 0
            now = departure_time_mins
            prev = 0
            for stop in route:
                node = self.node_by_id[stop["id"]]
                idx = self.index[node["id"]]
                leg_dist = distances[prev][idx]
                leg_time = times[prev][idx]
                total_distance += leg_dist
                total_time += leg_time
                now += leg_time
                if now < node["ready"]:
                    total_early += node["ready"] - now
                    now = float(node["ready"])
                if now > node["due"]:
                    time_window_violations += 1
                    total_lateness += now - node["due"]
                load += node["demand"]
                now += node["service"]
                prev = idx

            total_distance += distances[prev][0]
            leg_time = times[prev][0]
            total_time += leg_time
            now += leg_time
            if now > self.instance.depot["due"]:
                time_window_violations += 1
                total_lateness += now - self.instance.depot["due"]
            if load > cap:
                capacity_violations += 1

        violations = capacity_violations + time_window_violations
        objective = (
            violations * self._VIOLATION_WEIGHT
            + len(routes) * self._VEHICLE_WEIGHT
            + total_distance
            + total_lateness * 1_000.0
        )
        penalty = objective - len(routes) * self._VEHICLE_WEIGHT - total_distance
        return EvaluationResult(
            total_distance=total_distance,
            total_travel_time=total_time,
            total_early_arrival=total_early,
            total_late_arrival=total_lateness,
            capacity_violations=capacity_violations,
            ride_time_violations=0,
            early_penalty=0.0,
            late_penalty=total_lateness * 1_000.0,
            capacity_penalty=capacity_violations * self._VIOLATION_WEIGHT,
            ride_time_penalty=0.0,
            total_penalty=penalty,
            objective_value=objective,
            time_window_violations=time_window_violations,
            time_window_lateness=total_lateness,
        )


def _make_sweep_seed(instance: SolomonInstance) -> list[list[dict[str, Any]]]:
    # Sweep uses Haversine only for its duration guard. Set that guard above the
    # full Solomon horizon; capacity clustering and polar ordering remain active.
    vehicles = [
        {"id": f"V{i + 1}", "capacity": instance.capacity}
        for i in range(instance.vehicle_count)
    ]
    return SweepClusterer().create_initial_routes(
        instance.depot,
        instance.customers,
        vehicles,
        max_route_duration_minutes=1_000_000.0,
        max_passenger_capacity=instance.capacity,
        enforce_min_vehicles_for_60_students=False,
    )


class SolomonTabuOptimizer(TabuSearchOptimizer):
    """Same move set and uniform candidate sampling, with copies made afterward.

    The project optimizer deep-copies every candidate before reducing its
    neighborhood to 80 moves. Here we first sample the same uniformly sampled
    move descriptors, then deep-copy only the retained candidates. This keeps
    the Tabu search policy while making 100-customer runs practical.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.iterations_executed = 0

    def generate_neighborhood(
        self, routes: list[list[dict[str, Any]]]
    ) -> list[tuple[list[list[dict[str, Any]]], tuple[str, Any, Any]]]:
        self.iterations_executed += 1
        moves: list[tuple[Any, ...]] = []
        for r_idx, route in enumerate(routes):
            for i in range(len(route) - 2):
                for j in range(i + 2, len(route)):
                    moves.append(("2opt", r_idx, i, j, ("2opt", r_idx, (i, j))))

        for r1 in range(len(routes)):
            for r2 in range(r1, len(routes)):
                for i, stop1 in enumerate(routes[r1]):
                    start_j = i + 1 if r1 == r2 else 0
                    for j in range(start_j, len(routes[r2])):
                        stop2 = routes[r2][j]
                        move_key = ("swap", min(stop1.get("id", i), stop2.get("id", j)),
                                    max(stop1.get("id", i), stop2.get("id", j)))
                        moves.append(("swap", r1, r2, i, j, move_key))

        for r1, source in enumerate(routes):
            for r2, target in enumerate(routes):
                if len(source) <= 1 and r1 == r2:
                    continue
                positions = range(len(target) + 1) if r1 != r2 else range(len(target))
                for i, stop in enumerate(source):
                    for pos in positions:
                        if r1 == r2 and pos in (i, i + 1):
                            continue
                        moves.append(("relocate", r1, r2, i, pos,
                                      ("relocate", stop.get("id", i), (r2, pos))))

        one_route_demand = (
            sum(int(stop.get("demand", stop.get("pickup_student_count", 1)))
                for route in routes for stop in route)
            if len(routes) == 1 else None
        )
        limit = 500 if len(routes) == 1 and one_route_demand <= 29 else 80
        selected = random.sample(moves, limit) if len(moves) > limit else moves
        candidates = []
        for move in selected:
            kind, *data = move
            new_routes = copy.deepcopy(routes)
            if kind == "2opt":
                r_idx, i, j, move_key = data
                new_routes[r_idx][i:j + 1] = reversed(new_routes[r_idx][i:j + 1])
            elif kind == "swap":
                r1, r2, i, j, move_key = data
                new_routes[r1][i], new_routes[r2][j] = new_routes[r2][j], new_routes[r1][i]
            else:
                r1, r2, i, pos, move_key = data
                stop = new_routes[r1].pop(i)
                new_routes[r2].insert(pos if r1 != r2 or pos < i else pos - 1, stop)
                new_routes = [route for route in new_routes if route]
            candidates.append((new_routes, move_key))
        return candidates


def run_benchmark(
    instance: SolomonInstance,
    iterations: int = 300,
    seed: int = 42,
) -> dict[str, Any]:
    evaluator = SolomonEvaluator(instance)
    initial_routes = _make_sweep_seed(instance)
    capacities = [instance.capacity] * instance.vehicle_count
    initial = evaluator.evaluate_solution(
        initial_routes, instance.depot, evaluator.distance, evaluator.travel_time,
        evaluator.index, capacities,
    )
    bks_validation = None
    if instance.name == "C101":
        bks_routes = [[instance.customers[node - 1] for node in route] for route in C101_BKS_ROUTES]
        bks_result = evaluator.evaluate_solution(
            bks_routes, instance.depot, evaluator.distance, evaluator.travel_time,
            evaluator.index, capacities,
        )
        bks_validation = {
            "vehicles": len(bks_routes),
            "distance": bks_result.total_distance,
            "capacity_violations": bks_result.capacity_violations,
            "time_window_violations": bks_result.time_window_violations,
            "feasible": bks_result.is_feasible(),
            "matches_published_distance": bks_result.total_distance == 828.94,
        }

    optimizer = SolomonTabuOptimizer(
        evaluator=evaluator,
        max_iterations=iterations,
    )
    random.seed(seed)
    started = time.perf_counter()
    routes, result = optimizer.optimize(
        initial_routes,
        instance.depot,
        evaluator.distance,
        evaluator.travel_time,
        evaluator.index,
        capacities,
        0.0,
        None,
        "PICKUP",
    )
    runtime = time.perf_counter() - started
    visits = [stop["id"] for route in routes for stop in route]
    expected = {customer["id"] for customer in instance.customers}
    missing = sorted(expected - set(visits), key=int)
    duplicate = sorted({node for node in visits if visits.count(node) > 1}, key=int)
    feasible = (
        not missing and not duplicate and result.capacity_violations == 0
        and result.time_window_violations == 0
    )
    bks = instance.best_known_distance
    return {
        "instance": instance.name,
        "customers": len(instance.customers),
        "fleet_available": instance.vehicle_count,
        "capacity": instance.capacity,
        "total_demand": sum(c["demand"] for c in instance.customers),
        "objective_order": "feasible first, then vehicles, then distance",
        "initial": {
            "vehicles": len(initial_routes), "distance": initial.total_distance,
            "capacity_violations": initial.capacity_violations,
            "time_window_violations": initial.time_window_violations,
            "lateness": initial.time_window_lateness,
        },
        "tabu": {
            "vehicles": len(routes), "distance": result.total_distance,
            "capacity_violations": result.capacity_violations,
            "time_window_violations": result.time_window_violations,
            "lateness": result.time_window_lateness,
            "feasible": feasible, "missing_customers": missing,
            "duplicate_customers": duplicate,
            "runtime_seconds": round(runtime, 3),
            "iteration_limit": iterations,
            "iterations_executed": optimizer.iterations_executed,
        },
        "bks": {
            "vehicles": instance.best_known_vehicles,
            "distance": bks,
            "distance_gap_percent": (
                round((result.total_distance - bks) / bks * 100.0, 2)
                if feasible and bks else None
            ),
            "evaluator_validation": bks_validation,
        },
        "seed": seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path, help="Path to a Solomon .txt instance")
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    instance = load_solomon_instance(args.instance)
    if instance.name == "C101":
        instance = SolomonInstance(**{
            **instance.__dict__, "best_known_vehicles": 10, "best_known_distance": 828.94,
        })
    print(json.dumps(run_benchmark(instance, args.iterations, args.seed), indent=2))


if __name__ == "__main__":
    main()
