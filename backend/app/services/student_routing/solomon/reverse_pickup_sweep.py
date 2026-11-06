"""Feasible-first polar sweep constructor for a Reverse-Pickup Solomon instance."""
from __future__ import annotations

from math import atan2, pi
from typing import Any

from .reverse_pickup_evaluator import ReversePickupEvaluator


class ReversePickupSweep:
    def __init__(self, evaluator: ReversePickupEvaluator):
        self.evaluator = evaluator

    def _angle(self, station: dict[str, Any]) -> float:
        depot = self.evaluator.depot
        angle = atan2(station["y"] - depot["y"], station["x"] - depot["x"])
        return angle + 2 * pi if angle < 0 else angle

    def create_initial_routes(self) -> list[list[dict[str, Any]]]:
        """Sweep by polar angle with feasible insertion into an existing sweep cluster.

        Keeping only one open route would create dozens of routes for C101's
        tight windows.  This still processes stations in polar sweep order, but
        lets a station join the least-cost existing cluster when a feasible
        insertion position exists.
        """
        routes: list[list[dict[str, Any]]] = []
        for station in sorted(self.evaluator.instance["stations"], key=self._angle):
            best: tuple[float, int, list[dict[str, Any]]] | None = None
            for route_index, route in enumerate(routes):
                for position in range(len(route) + 1):
                    candidate = [*route[:position], station, *route[position:]]
                    evaluation = self.evaluator.evaluate_route(candidate)
                    if evaluation.is_feasible:
                        candidate_cost = evaluation.route_distance
                        if best is None or candidate_cost < best[0]:
                            best = (candidate_cost, route_index, candidate)
            if best is None:
                routes.append([station])
            else:
                _, route_index, candidate = best
                routes[route_index] = candidate
        return routes
