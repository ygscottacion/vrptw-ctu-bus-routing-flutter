"""Pure evaluator for Solomon Reverse-Pickup; intentionally independent of CTU rules."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Iterable


@dataclass(frozen=True)
class RouteEvaluation:
    route_distance: float
    travel_time: float
    service_time: float
    return_time: float
    total_demand: int
    capacity_violations: int
    time_window_violations: int
    depot_window_violations: int
    stops: list[dict[str, Any]]

    @property
    def is_feasible(self) -> bool:
        return not (self.capacity_violations or self.time_window_violations or self.depot_window_violations)


def euclidean_matrix(nodes: list[dict[str, Any]]) -> list[list[float]]:
    return [[hypot(a["x"] - b["x"], a["y"] - b["y"]) for b in nodes] for a in nodes]


class ReversePickupEvaluator:
    def __init__(self, instance: dict[str, Any]):
        self.instance = instance
        self.depot = instance["depot"]
        self.capacity = int(instance["fleet"]["vehicle_capacity"])
        self.nodes = [self.depot, *instance["stations"]]
        self.index = {node["id"]: index for index, node in enumerate(self.nodes)}
        self.matrix = euclidean_matrix(self.nodes)

    def distance(self, left: dict[str, Any], right: dict[str, Any]) -> float:
        return self.matrix[self.index[left["id"]]][self.index[right["id"]]]

    def evaluate_route(self, route: Iterable[dict[str, Any]]) -> RouteEvaluation:
        current = self.depot
        current_time = float(self.depot["time_window_start"])
        route_distance = travel_time = service_time = 0.0
        load = capacity_violations = tw_violations = 0
        stops: list[dict[str, Any]] = []
        for station in route:
            leg = self.distance(current, station)
            route_distance += leg
            travel_time += leg
            arrival = current_time + leg
            service_start = max(arrival, float(station["time_window_start"]))
            if service_start > float(station["time_window_end"]):
                tw_violations += 1
            departure = service_start + float(station["service_time"])
            load += int(station["demand"])
            if load > self.capacity:
                capacity_violations += 1
            service_time += float(station["service_time"])
            stops.append({
                "id": station["id"], "source_customer_id": station["source_customer_id"],
                "arrival_time": arrival, "service_start_time": service_start, "departure_time": departure,
                "demand": station["demand"], "cumulative_load": load,
                "time_window_start": station["time_window_start"], "time_window_end": station["time_window_end"],
                "service_time": station["service_time"],
            })
            current, current_time = station, departure
        back = self.distance(current, self.depot) if stops else 0.0
        route_distance += back
        travel_time += back
        return_time = current_time + back
        depot_violations = int(return_time > float(self.depot["time_window_end"]))
        return RouteEvaluation(route_distance, travel_time, service_time, return_time, load,
                               capacity_violations, tw_violations, depot_violations, stops)

    def evaluate_solution(self, routes: list[list[dict[str, Any]]]) -> dict[str, Any]:
        evaluations = [self.evaluate_route(route) for route in routes if route]
        capacity = sum(value.capacity_violations for value in evaluations)
        windows = sum(value.time_window_violations for value in evaluations)
        depot = sum(value.depot_window_violations for value in evaluations)
        fleet = int(len(evaluations) > int(self.instance["fleet"]["max_vehicles"]))
        return {
            "is_feasible": not (capacity or windows or depot or fleet), "vehicles_used": len(evaluations),
            "total_distance": sum(value.route_distance for value in evaluations),
            "total_travel_time": sum(value.travel_time for value in evaluations),
            "total_service_time": sum(value.service_time for value in evaluations),
            "capacity_violations": capacity, "time_window_violations": windows,
            "depot_window_violations": depot, "route_evaluations": evaluations,
            "fleet_violations": fleet,
        }
