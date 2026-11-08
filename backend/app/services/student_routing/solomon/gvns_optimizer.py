"""General VNS for the isolated Solomon Reverse-Pickup benchmark only."""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from random import Random
from typing import Any

from .reverse_pickup_evaluator import ReversePickupEvaluator

Solution = list[list[dict[str, Any]]]
Evaluation = dict[str, Any]


@dataclass(frozen=True)
class GVNSConfig:
    max_iterations: int = 10_000
    max_runtime_seconds: float = 5.0
    candidates_per_neighborhood: int = 500


def report_score(evaluation: Evaluation) -> tuple[int, int, float]:
    return (0 if evaluation["is_feasible"] else 1, int(evaluation["vehicles_used"]),
            float(evaluation["total_distance"]))


def guided_score(evaluation: Evaluation) -> tuple[int, int, int, int, int, int, float]:
    """Search-only ordering; public results still use ``report_score``."""
    if evaluation["is_feasible"]:
        return (0, 0, 0, 0, 0, int(evaluation["vehicles_used"]), float(evaluation["total_distance"]))
    return (1, int(evaluation["fleet_violations"]), int(evaluation["capacity_violations"]),
            int(evaluation["time_window_violations"]), int(evaluation["depot_window_violations"]),
            int(evaluation["vehicles_used"]), float(evaluation["total_distance"]))


def _ids(solution: Solution) -> list[str]:
    return [station["id"] for route in solution for station in route]


def assert_coverage(solution: Solution, expected: set[str]) -> None:
    values = _ids(solution)
    if len(values) != len(set(values)) or set(values) != expected:
        raise ValueError("GVNS move lost or duplicated a Solomon station")


def _moves(solution: Solution, kind: str) -> list[tuple[Any, ...]]:
    result: list[tuple[Any, ...]] = []
    if kind == "2opt":
        for route_index, route in enumerate(solution):
            if len(route) >= 4:
                result.extend((route_index, left, right) for left in range(len(route) - 2)
                              for right in range(left + 2, len(route)))
    elif kind == "swap":
        positions = [(route_index, stop_index) for route_index, route in enumerate(solution)
                     for stop_index in range(len(route))]
        result.extend((a, b, c, d) for index, (a, b) in enumerate(positions)
                      for c, d in positions[index + 1:])
    else:
        for source, route in enumerate(solution):
            for item_index in range(len(route)):
                for target, target_route in enumerate(solution):
                    for position in range(len(target_route) + 1):
                        if source != target or position not in (item_index, item_index + 1):
                            result.append((source, item_index, target, position))
    return result


def apply_move(solution: Solution, kind: str, move: tuple[Any, ...]) -> Solution:
    candidate = copy.deepcopy(solution)
    if kind == "2opt":
        route, left, right = move
        candidate[route][left:right + 1] = reversed(candidate[route][left:right + 1])
    elif kind == "swap":
        first_route, first_stop, second_route, second_stop = move
        candidate[first_route][first_stop], candidate[second_route][second_stop] = (
            candidate[second_route][second_stop], candidate[first_route][first_stop])
    else:
        source, item_index, target, position = move
        item = candidate[source].pop(item_index)
        insert_at = position if source != target or position < item_index else position - 1
        candidate[target].insert(insert_at, item)
        candidate = [route for route in candidate if route]
    return candidate


class SolomonGVNSOptimizer:
    vnd_neighborhoods = ("2opt", "swap", "relocate")
    shaking_neighborhoods = ("relocate_1", "swap_1", "relocate_2_3")

    def __init__(self, evaluator: ReversePickupEvaluator, config: GVNSConfig | None = None,
                 rng: Random | None = None) -> None:
        self.evaluator, self.config, self.rng = evaluator, config or GVNSConfig(), rng or Random()

    def _shaking(self, solution: Solution, level: int, expected: set[str]) -> Solution:
        result = copy.deepcopy(solution)
        kinds = ["relocate"] if level == 0 else ["swap"] if level == 1 else ["relocate"]
        count = 1 if level < 2 else self.rng.randint(2, 3)
        for _ in range(count):
            moves = _moves(result, kinds[0])
            if not moves:
                break
            result = apply_move(result, kinds[0], self.rng.choice(moves))
            assert_coverage(result, expected)
        return result

    def optimize(self, initial_solution: Solution) -> tuple[Solution, Evaluation, dict[str, Any]]:
        expected = set(_ids(initial_solution))
        current = copy.deepcopy([route for route in initial_solution if route])
        assert_coverage(current, expected)
        best = copy.deepcopy(current)
        best_eval = self.evaluator.evaluate_solution(best)
        started, iteration, evaluations, level = time.perf_counter(), 0, 1, 0
        stop_reason = "max_iterations"
        shaking_attempts = {name: 0 for name in self.shaking_neighborhoods}
        candidate_counts = {name: 0 for name in self.vnd_neighborhoods}
        feasible = infeasible = improved = 0
        history = [{"iteration": 0, "vehicles_used": best_eval["vehicles_used"],
                    "total_distance": best_eval["total_distance"]}]

        while iteration < self.config.max_iterations:
            if time.perf_counter() >= started + self.config.max_runtime_seconds:
                stop_reason = "time_limit"
                break
            shaking_attempts[self.shaking_neighborhoods[level]] += 1
            candidate = self._shaking(current, level, expected)
            candidate_eval = self.evaluator.evaluate_solution(candidate)
            evaluations += 1
            neighborhood_index = 0
            deadline = False
            # VND: an improving local move restarts from the first neighborhood.
            while neighborhood_index < len(self.vnd_neighborhoods):
                if time.perf_counter() >= started + self.config.max_runtime_seconds:
                    deadline = True
                    break
                kind = self.vnd_neighborhoods[neighborhood_index]
                moves = _moves(candidate, kind)
                sampled = self.rng.sample(moves, min(self.config.candidates_per_neighborhood, len(moves)))
                best_local: tuple[tuple[int, int, int, int, int, int, float], Solution, Evaluation] | None = None
                for move in sampled:
                    if time.perf_counter() >= started + self.config.max_runtime_seconds:
                        deadline = True
                        break
                    candidate_counts[kind] += 1
                    local = apply_move(candidate, kind, move)
                    assert_coverage(local, expected)
                    local_eval = self.evaluator.evaluate_solution(local)
                    evaluations += 1
                    if local_eval["is_feasible"]:
                        feasible += 1
                    else:
                        infeasible += 1
                    if report_score(local_eval) < report_score(best_eval):
                        improved += 1
                    item = (guided_score(local_eval), local, local_eval)
                    if best_local is None or item[0] < best_local[0]:
                        best_local = item
                if deadline:
                    break
                # VND only accepts a move that improves the current guided score.
                if best_local is not None and best_local[0] < guided_score(candidate_eval):
                    _, candidate, candidate_eval = best_local
                    neighborhood_index = 0
                else:
                    neighborhood_index += 1
            iteration += 1
            if report_score(candidate_eval) < report_score(best_eval):
                best, best_eval, current, level = copy.deepcopy(candidate), candidate_eval, candidate, 0
                history.append({"iteration": iteration, "vehicles_used": best_eval["vehicles_used"],
                                "total_distance": best_eval["total_distance"]})
            else:
                current = candidate
                level = (level + 1) % len(self.shaking_neighborhoods)
            if deadline:
                stop_reason = "time_limit"
                break
        return best, best_eval, {
            "max_iterations": self.config.max_iterations, "max_runtime_seconds": self.config.max_runtime_seconds,
            "iterations_completed": iteration, "evaluations_completed": evaluations, "stop_reason": stop_reason,
            "gvns_diagnostics": {"vnd_neighborhoods": list(self.vnd_neighborhoods),
                "shaking_neighborhoods": list(self.shaking_neighborhoods),
                "candidates_per_neighborhood": self.config.candidates_per_neighborhood,
                "shaking_attempts": shaking_attempts, "vnd_candidate_counts": candidate_counts,
                "feasible_candidates_evaluated": feasible, "infeasible_candidates_evaluated": infeasible,
                "improving_candidates_found": improved, "best_distance_by_iteration": history},
        }
