"""Adaptive Large Neighborhood Search for the isolated Solomon benchmark.

This module deliberately depends only on ``ReversePickupEvaluator``.  It does
not import production CTU configuration, routing services, or database code.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, hypot
from random import Random
from typing import Any, Callable
import copy

from .reverse_pickup_evaluator import ReversePickupEvaluator

Solution = list[list[dict[str, Any]]]
Evaluation = dict[str, Any]


@dataclass(frozen=True)
class ALNSConfig:
    # The wall-clock budget is the benchmark's primary stopping condition.
    # Keep this only as a protective ceiling so ALNS does not stop at 200
    # iterations before a shared 5-second Tabu budget is consumed.
    max_iterations: int = 10_000
    max_runtime_seconds: float = 5.0
    min_removal: int = 5
    max_removal: int = 20
    removal_fraction: float = 0.20
    segment_length: int = 25
    reaction_factor: float = 0.20
    sigma_1: float = 8.0
    sigma_2: float = 4.0
    sigma_3: float = 1.0
    sigma_4: float = 0.0
    initial_temperature: float = 20.0
    cooling_rate: float = 0.995
    temperature_min: float = 0.01


def score(evaluation: Evaluation) -> tuple[int, int, float]:
    """The benchmark's lexicographic objective: feasible, vehicles, distance."""
    return (
        0 if evaluation["is_feasible"] else 1,
        int(evaluation["vehicles_used"]),
        float(evaluation["total_distance"]),
    )


def _clean(solution: Solution) -> Solution:
    return [route for route in solution if route]


def _station_lookup(solution: Solution) -> list[dict[str, Any]]:
    return [station for route in solution for station in route]


def _remove_ids(solution: Solution, ids: set[str]) -> tuple[Solution, list[dict[str, Any]]]:
    removed = [station for station in _station_lookup(solution) if station["id"] in ids]
    partial = [[station for station in route if station["id"] not in ids] for route in solution]
    return _clean(partial), removed


def random_removal(solution: Solution, q: int, rng: Random, evaluator: ReversePickupEvaluator) -> tuple[Solution, list[dict[str, Any]]]:
    del evaluator
    stations = _station_lookup(solution)
    selected = rng.sample(stations, min(q, len(stations)))
    return _remove_ids(solution, {station["id"] for station in selected})


def _route_distance(route: list[dict[str, Any]], evaluator: ReversePickupEvaluator) -> float:
    return evaluator.evaluate_route(route).route_distance


def worst_removal(solution: Solution, q: int, rng: Random, evaluator: ReversePickupEvaluator) -> tuple[Solution, list[dict[str, Any]]]:
    """Remove stations with the largest marginal Euclidean-distance saving."""
    savings: list[tuple[float, dict[str, Any]]] = []
    for route in solution:
        before = _route_distance(route, evaluator)
        for index, station in enumerate(route):
            without = [*route[:index], *route[index + 1:]]
            savings.append((before - _route_distance(without, evaluator), station))
    # Shuffle equal values reproducibly, then take the largest savings.
    rng.shuffle(savings)
    savings.sort(key=lambda item: item[0], reverse=True)
    selected = [station for _, station in savings[:min(q, len(savings))]]
    return _remove_ids(solution, {station["id"] for station in selected})


def _relatedness(left: dict[str, Any], right: dict[str, Any]) -> float:
    geographic = hypot(left["x"] - right["x"], left["y"] - right["y"])
    temporal = abs(left["time_window_start"] - right["time_window_start"]) + abs(
        left["time_window_end"] - right["time_window_end"]
    )
    demand = abs(left["demand"] - right["demand"])
    return geographic + 0.05 * temporal + 0.10 * demand


def related_removal(solution: Solution, q: int, rng: Random, evaluator: ReversePickupEvaluator) -> tuple[Solution, list[dict[str, Any]]]:
    del evaluator
    stations = _station_lookup(solution)
    if not stations:
        return [], []
    seed = rng.choice(stations)
    ranked = [station for station in stations if station["id"] != seed["id"]]
    rng.shuffle(ranked)
    ranked.sort(key=lambda station: _relatedness(seed, station))
    selected = [seed, *ranked[:max(0, min(q, len(stations)) - 1)]]
    return _remove_ids(solution, {station["id"] for station in selected})


def route_removal(solution: Solution, q: int, rng: Random, evaluator: ReversePickupEvaluator) -> tuple[Solution, list[dict[str, Any]]]:
    del evaluator
    remaining = [list(route) for route in solution if route]
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < q:
        route = remaining.pop(rng.randrange(len(remaining)))
        selected.extend(route)
    if len(selected) > q:
        # Retain q random stations; the other stations remain in their routes.
        chosen = rng.sample(selected, q)
        return _remove_ids(solution, {station["id"] for station in chosen})
    return _remove_ids(solution, {station["id"] for station in selected})


DestroyOperator = Callable[[Solution, int, Random, ReversePickupEvaluator], tuple[Solution, list[dict[str, Any]]]]


def _insertion_options(solution: Solution, station: dict[str, Any], evaluator: ReversePickupEvaluator) -> list[tuple[float, Solution]]:
    """Return feasible insertions, ranked by pure route-distance increase."""
    options: list[tuple[float, Solution]] = []
    for route_index, route in enumerate(solution):
        before = _route_distance(route, evaluator)
        for position in range(len(route) + 1):
            candidate_route = [*route[:position], station, *route[position:]]
            if not evaluator.evaluate_route(candidate_route).is_feasible:
                continue
            candidate = copy.deepcopy(solution)
            candidate[route_index] = candidate_route
            options.append((_route_distance(candidate_route, evaluator) - before, candidate))
    if len(solution) < int(evaluator.instance["fleet"]["max_vehicles"]):
        candidate = [*copy.deepcopy(solution), [station]]
        if evaluator.evaluate_route([station]).is_feasible:
            options.append((_route_distance([station], evaluator), candidate))
    return options


def _least_bad_insertion(solution: Solution, station: dict[str, Any], evaluator: ReversePickupEvaluator) -> Solution:
    """Transparent fallback: preserve coverage and let the evaluator expose violations."""
    candidates: list[Solution] = []
    for route_index, route in enumerate(solution):
        for position in range(len(route) + 1):
            candidate = copy.deepcopy(solution)
            candidate[route_index].insert(position, station)
            candidates.append(candidate)
    if len(solution) < int(evaluator.instance["fleet"]["max_vehicles"]):
        candidates.append([*copy.deepcopy(solution), [station]])
    if not candidates:
        candidates = [[station]]
    return min(candidates, key=lambda candidate: score(evaluator.evaluate_solution(candidate)))


def greedy_insertion(partial: Solution, removed: list[dict[str, Any]], rng: Random,
                     evaluator: ReversePickupEvaluator) -> Solution:
    del rng
    solution = copy.deepcopy(partial)
    for station in removed:
        options = _insertion_options(solution, station, evaluator)
        solution = min(options, key=lambda item: item[0])[1] if options else _least_bad_insertion(solution, station, evaluator)
    return _clean(solution)


def regret_2_insertion(partial: Solution, removed: list[dict[str, Any]], rng: Random,
                       evaluator: ReversePickupEvaluator) -> Solution:
    del rng
    solution, pending = copy.deepcopy(partial), list(removed)
    while pending:
        ranked: list[tuple[float, float, dict[str, Any], Solution | None]] = []
        for station in pending:
            options = sorted(_insertion_options(solution, station, evaluator), key=lambda item: item[0])
            if not options:
                ranked.append((float("inf"), float("inf"), station, None))
            elif len(options) == 1:
                ranked.append((float("inf"), options[0][0], station, options[0][1]))
            else:
                ranked.append((options[1][0] - options[0][0], options[0][0], station, options[0][1]))
        # Largest regret first; distance resolves equal regret deterministically.
        regret, _, station, selected = max(ranked, key=lambda item: (item[0], -item[1], item[2]["id"]))
        del regret
        solution = selected if selected is not None else _least_bad_insertion(solution, station, evaluator)
        pending.remove(station)
    return _clean(solution)


RepairOperator = Callable[[Solution, list[dict[str, Any]], Random, ReversePickupEvaluator], Solution]


class SolomonALNSOptimizer:
    """ALNS using four destroy and two repair operators for Reverse-Pickup VRPTW."""

    destroy_operators: dict[str, DestroyOperator] = {
        "random_removal": random_removal,
        "worst_removal": worst_removal,
        "related_removal": related_removal,
        "route_removal": route_removal,
    }
    repair_operators: dict[str, RepairOperator] = {
        "greedy_insertion": greedy_insertion,
        "regret_2_insertion": regret_2_insertion,
    }

    def __init__(self, evaluator: ReversePickupEvaluator, config: ALNSConfig | None = None,
                 rng: Random | None = None):
        self.evaluator = evaluator
        self.config = config or ALNSConfig()
        self.rng = rng or Random()

    def _select(self, weights: dict[str, float]) -> str:
        total = sum(weights.values())
        threshold = self.rng.random() * total
        cumulative = 0.0
        for name, weight in weights.items():
            cumulative += weight
            if cumulative >= threshold:
                return name
        return next(reversed(weights))

    def _removal_size(self, solution: Solution) -> int:
        total = len(_station_lookup(solution))
        upper = min(self.config.max_removal, max(self.config.min_removal, int(self.config.removal_fraction * total)))
        lower = min(self.config.min_removal, total)
        return self.rng.randint(lower, min(upper, total))

    def _accept(self, current: Evaluation, candidate: Evaluation, temperature: float) -> bool:
        current_score, candidate_score = score(current), score(candidate)
        if candidate_score < current_score:
            return True
        # SA only applies for equally feasible, equally sized fleet solutions.
        if current_score[:2] != candidate_score[:2]:
            return False
        delta = candidate_score[2] - current_score[2]
        return delta <= 0 or self.rng.random() < exp(-delta / max(temperature, self.config.temperature_min))

    @staticmethod
    def _update_weights(weights: dict[str, float], scores: dict[str, float], usages: dict[str, int], reaction: float) -> None:
        for name, old_weight in weights.items():
            if usages[name]:
                weights[name] = (1 - reaction) * old_weight + reaction * (scores[name] / usages[name])

    def optimize(self, initial_solution: Solution, clock: Callable[[], float]) -> tuple[Solution, Evaluation, dict[str, Any]]:
        current = copy.deepcopy(_clean(initial_solution))
        current_eval = self.evaluator.evaluate_solution(current)
        best, best_eval = copy.deepcopy(current), current_eval
        destroy_weights = {name: 1.0 for name in self.destroy_operators}
        repair_weights = {name: 1.0 for name in self.repair_operators}
        destroy_usage = {name: 0 for name in destroy_weights}
        repair_usage = {name: 0 for name in repair_weights}
        segment_destroy_scores = {name: 0.0 for name in destroy_weights}
        segment_repair_scores = {name: 0.0 for name in repair_weights}
        segment_destroy_usage = {name: 0 for name in destroy_weights}
        segment_repair_usage = {name: 0 for name in repair_weights}
        started, temperature, iterations, evaluations = clock(), self.config.initial_temperature, 0, 1

        stop_reason = "max_iterations"
        while iterations < self.config.max_iterations and clock() - started < self.config.max_runtime_seconds:
            destroy_name, repair_name = self._select(destroy_weights), self._select(repair_weights)
            q = self._removal_size(current)
            partial, removed = self.destroy_operators[destroy_name](copy.deepcopy(current), q, self.rng, self.evaluator)
            candidate = self.repair_operators[repair_name](partial, removed, self.rng, self.evaluator)
            candidate_eval = self.evaluator.evaluate_solution(candidate)
            evaluations += 1
            was_global_best = score(candidate_eval) < score(best_eval)
            accepted = self._accept(current_eval, candidate_eval, temperature)
            reward = self.config.sigma_4
            if was_global_best:
                best, best_eval, reward = copy.deepcopy(candidate), candidate_eval, self.config.sigma_1
            if accepted:
                if not was_global_best and score(candidate_eval) < score(current_eval):
                    reward = self.config.sigma_2
                elif not was_global_best:
                    reward = self.config.sigma_3
                current, current_eval = candidate, candidate_eval
            destroy_usage[destroy_name] += 1
            repair_usage[repair_name] += 1
            segment_destroy_usage[destroy_name] += 1
            segment_repair_usage[repair_name] += 1
            segment_destroy_scores[destroy_name] += reward
            segment_repair_scores[repair_name] += reward
            iterations += 1
            temperature = max(self.config.temperature_min, temperature * self.config.cooling_rate)
            if iterations % self.config.segment_length == 0:
                self._update_weights(destroy_weights, segment_destroy_scores, segment_destroy_usage, self.config.reaction_factor)
                self._update_weights(repair_weights, segment_repair_scores, segment_repair_usage, self.config.reaction_factor)
                segment_destroy_scores = {name: 0.0 for name in destroy_weights}
                segment_repair_scores = {name: 0.0 for name in repair_weights}
                segment_destroy_usage = {name: 0 for name in destroy_weights}
                segment_repair_usage = {name: 0 for name in repair_weights}

        if clock() - started >= self.config.max_runtime_seconds:
            stop_reason = "time_limit"

        return best, best_eval, {
            "max_iterations": self.config.max_iterations,
            "max_runtime_seconds": self.config.max_runtime_seconds,
            "iterations_completed": iterations,
            "evaluations_completed": evaluations,
            "stop_reason": stop_reason,
            "destroy": {name: {"usage_count": destroy_usage[name], "final_weight": destroy_weights[name]} for name in destroy_weights},
            "repair": {name: {"usage_count": repair_usage[name], "final_weight": repair_weights[name]} for name in repair_weights},
        }
