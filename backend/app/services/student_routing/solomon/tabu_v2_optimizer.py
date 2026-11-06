"""Production-inspired Tabu Search for the isolated Solomon benchmark.

This module intentionally reimplements the *mechanisms* of the CTU Tabu
optimizer (move-based tabu list, dynamic tenure, aspiration and
diversification), while keeping Solomon's independent evaluator and rules.
It must never be imported by the CTU production routing pipeline.
"""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from random import Random
from typing import Any, Literal

from .reverse_pickup_evaluator import ReversePickupEvaluator

Solution = list[list[dict[str, Any]]]
Evaluation = dict[str, Any]
MoveKind = Literal["2opt", "swap", "relocate"]
Move = tuple[MoveKind, tuple[Any, ...]]


@dataclass(frozen=True)
class TabuV2Config:
    max_iterations: int = 10_000
    max_runtime_seconds: float = 5.0
    base_tenure: int = 10
    diversify_rounds: int = 15
    early_stopping_rounds: int | None = None
    # C201 has a sparse feasible neighbourhood under reverse time windows.
    # A fixed 500-move sample gives all benchmark instances adequate coverage
    # while the shared wall-clock limit remains the fairness constraint.
    candidates_per_iteration: int = 500


def report_score(evaluation: Evaluation) -> tuple[int, int, float]:
    """Objective reported in the study: feasibility, fleet size, distance."""
    return (
        0 if evaluation["is_feasible"] else 1,
        int(evaluation["vehicles_used"]),
        float(evaluation["total_distance"]),
    )


def guided_score(evaluation: Evaluation) -> tuple[int, int, int, int, int, int, float]:
    """Search-only score which gives infeasible solutions a meaningful order.

    The original benchmark treated every infeasible candidate as tied before
    vehicle count and distance.  That allowed a severely infeasible candidate
    to win merely because it was short.  This score preserves the study's
    feasible-first objective while guiding a temporary infeasible walk back
    towards feasibility.  It is never used as a reported result objective.
    """
    if evaluation["is_feasible"]:
        return (0, 0, 0, 0, 0, int(evaluation["vehicles_used"]), float(evaluation["total_distance"]))
    return (
        1,
        int(evaluation["fleet_violations"]),
        int(evaluation["capacity_violations"]),
        int(evaluation["time_window_violations"]),
        int(evaluation["depot_window_violations"]),
        int(evaluation["vehicles_used"]),
        float(evaluation["total_distance"]),
    )


class MoveTabuList:
    """Move-key tabu list with the same aspiration policy as production."""

    def __init__(self, tenure: int) -> None:
        self.tenure = tenure
        self._expires_at: dict[Move, int] = {}

    def add(self, move: Move, iteration: int) -> None:
        self._expires_at[move] = iteration + self.tenure

    def is_tabu(self, move: Move, iteration: int, candidate: Evaluation, global_best: Evaluation) -> bool:
        if self._expires_at.get(move, -1) <= iteration:
            return False
        # Aspiration uses exactly the public, lexicographic benchmark objective.
        return report_score(candidate) >= report_score(global_best)


def _all_moves(solution: Solution) -> list[Move]:
    """Enumerate descriptors first, then sample them without copying solutions."""
    moves: list[Move] = []
    for route_index, route in enumerate(solution):
        if len(route) >= 4:
            for start in range(len(route) - 2):
                for end in range(start + 2, len(route)):
                    moves.append(("2opt", (route_index, start, end)))

    for first_route, route_one in enumerate(solution):
        for second_route in range(first_route, len(solution)):
            route_two = solution[second_route]
            for first_stop, station_one in enumerate(route_one):
                start_second = first_stop + 1 if first_route == second_route else 0
                for second_stop in range(start_second, len(route_two)):
                    station_two = route_two[second_stop]
                    first_id, second_id = sorted((station_one["id"], station_two["id"]))
                    moves.append(("swap", (first_route, first_stop, second_route, second_stop, first_id, second_id)))

    for source_route, route in enumerate(solution):
        for source_stop, station in enumerate(route):
            for target_route, target in enumerate(solution):
                for position in range(len(target) + 1):
                    if source_route == target_route and position in (source_stop, source_stop + 1):
                        continue
                    moves.append(("relocate", (source_route, source_stop, target_route, position, station["id"])))
    return moves


def _move_key(move: Move) -> Move:
    kind, values = move
    if kind == "2opt":
        route, start, end = values
        return kind, (route, start, end)
    if kind == "swap":
        *_, first_id, second_id = values
        return kind, (first_id, second_id)
    *_, station_id = values
    return kind, (station_id, values[2], values[3])


def _apply_move(solution: Solution, move: Move) -> Solution:
    candidate = copy.deepcopy(solution)
    kind, values = move
    if kind == "2opt":
        route, start, end = values
        candidate[route][start:end + 1] = reversed(candidate[route][start:end + 1])
    elif kind == "swap":
        first_route, first_stop, second_route, second_stop, *_ = values
        candidate[first_route][first_stop], candidate[second_route][second_stop] = (
            candidate[second_route][second_stop], candidate[first_route][first_stop]
        )
    else:
        source_route, source_stop, target_route, position, _ = values
        station = candidate[source_route].pop(source_stop)
        insert_at = position if source_route != target_route or position < source_stop else position - 1
        candidate[target_route].insert(insert_at, station)
        candidate = [route for route in candidate if route]
    return candidate


def _assert_coverage(solution: Solution, expected_ids: set[str]) -> None:
    ids = [station["id"] for route in solution for station in route]
    if len(ids) != len(set(ids)) or set(ids) != expected_ids:
        raise ValueError("A Tabu move lost or duplicated a Solomon station")


class SolomonTabuV2Optimizer:
    def __init__(self, evaluator: ReversePickupEvaluator, config: TabuV2Config | None = None,
                 rng: Random | None = None) -> None:
        self.evaluator = evaluator
        self.config = config or TabuV2Config()
        self.rng = rng or Random()

    def optimize(self, initial_solution: Solution) -> tuple[Solution, Evaluation, dict[str, Any]]:
        current = copy.deepcopy([route for route in initial_solution if route])
        expected_ids = {station["id"] for route in current for station in route}
        _assert_coverage(current, expected_ids)
        current_eval = self.evaluator.evaluate_solution(current)
        best, best_eval = copy.deepcopy(current), current_eval
        tabu = MoveTabuList(self.config.base_tenure)
        started = time.perf_counter()
        evaluations, iterations, stale, diversification_count = 1, 0, 0, 0
        candidate_counts = {"2opt": 0, "swap": 0, "relocate": 0}
        feasible_candidates = infeasible_candidates = improving_candidates = 0
        best_history = [{"iteration": 0, "vehicles_used": best_eval["vehicles_used"],
                         "total_distance": best_eval["total_distance"]}]
        stop_reason = "max_iterations"

        while iterations < self.config.max_iterations:
            if time.perf_counter() - started >= self.config.max_runtime_seconds:
                stop_reason = "time_limit"
                break
            tabu.tenure = max(3, self.config.base_tenure + self.rng.choice((-1, 0, 1)))
            all_moves = _all_moves(current)
            if not all_moves:
                stop_reason = "no_candidates"
                break
            sampled = self.rng.sample(all_moves, min(self.config.candidates_per_iteration, len(all_moves)))
            ranked: list[tuple[tuple[int, int, int, int, int, int, float], Solution, Evaluation, Move]] = []
            deadline_reached = False
            for move in sampled:
                if time.perf_counter() - started >= self.config.max_runtime_seconds:
                    deadline_reached = True
                    break
                kind, _ = move
                candidate_counts[kind] += 1
                candidate = _apply_move(current, move)
                _assert_coverage(candidate, expected_ids)
                evaluation = self.evaluator.evaluate_solution(candidate)
                evaluations += 1
                if evaluation["is_feasible"]:
                    feasible_candidates += 1
                else:
                    infeasible_candidates += 1
                if report_score(evaluation) < report_score(best_eval):
                    improving_candidates += 1
                move_key = _move_key(move)
                if not tabu.is_tabu(move_key, iterations, evaluation, best_eval):
                    ranked.append((guided_score(evaluation), candidate, evaluation, move_key))

            if not ranked:
                stop_reason = "time_limit" if deadline_reached else "no_candidates"
                break
            _, next_solution, next_eval, next_move = min(ranked, key=lambda item: item[0])
            current, current_eval = next_solution, next_eval
            tabu.add(next_move, iterations)
            iterations += 1
            if report_score(current_eval) < report_score(best_eval):
                best, best_eval, stale = copy.deepcopy(current), current_eval, 0
                best_history.append({"iteration": iterations, "vehicles_used": best_eval["vehicles_used"],
                                     "total_distance": best_eval["total_distance"]})
            else:
                stale += 1

            if stale >= self.config.diversify_rounds:
                # Pick a reproducible feasible move if one exists; otherwise take
                # the least-violating evaluated candidate to preserve search flow.
                pool = [item for item in ranked if item[2]["is_feasible"]] or ranked
                _, current, current_eval, move_key = self.rng.choice(pool)
                tabu.add(move_key, iterations)
                stale = 0
                diversification_count += 1
            if self.config.early_stopping_rounds is not None and stale >= self.config.early_stopping_rounds:
                stop_reason = "early_stopping"
                break

        return best, best_eval, {
            "max_iterations": self.config.max_iterations,
            "max_runtime_seconds": self.config.max_runtime_seconds,
            "iterations_completed": iterations,
            "evaluations_completed": evaluations,
            "stop_reason": stop_reason,
            "tabu_diagnostics": {
                "base_tenure": self.config.base_tenure,
                "dynamic_tenure_enabled": True,
                "aspiration_enabled": True,
                "diversification_enabled": True,
                "diversification_count": diversification_count,
                "candidates_per_iteration": self.config.candidates_per_iteration,
                "candidate_counts": candidate_counts,
                "feasible_candidates_evaluated": feasible_candidates,
                "infeasible_candidates_evaluated": infeasible_candidates,
                "improving_candidates_found": improving_candidates,
                "best_distance_by_iteration": best_history,
            },
        }
