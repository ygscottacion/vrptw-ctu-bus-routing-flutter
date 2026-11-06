#!/usr/bin/env python3
"""Standalone CTU ALNS benchmark. Python 3.10+, standard library only.

Run: python ctu_alns_benchmark.py --iterations 300 --runs 5
The script uses no database, API keys, app package, or ticket/student data.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
import statistics
import time
from pathlib import Path


SESSION_ID = "MORNING_1"  # Valid production session; school starts at 07:00.
TRIP_TYPE = "PICKUP"
DEPOT = {
    "location_id": "1962227a-0153-4ea6-9051-59cc7194c32c",
    "location_code": "LOC-01",
    "lat": 10.0282,
    "lng": 105.7682,
}
VEHICLES = [
    {"id": "vehicle_1", "database_capacity": 30},
    {"id": "vehicle_2", "database_capacity": 30},
    {"id": "vehicle_3", "database_capacity": 30},
]

# Real geocoded locations read from the CTU database. Tuple order is latitude, longitude.
LOCATIONS = {
    "LOC-02": (10.032213, 105.787976),
    "LOC-03": (10.005198, 105.772084),
    "LOC-04": (10.024814, 105.767565),
    "LOC-05": (10.034498, 105.755812),
    "LOC-06": (10.030945, 105.781573),
    "LOC-07": (10.0422122960996, 105.766568219782),
    "LOC-08": (10.02480669983, 105.774475021185),
    "LOC-09": (10.0145617972912, 105.783011841603),
    "LOC-10": (10.0055227483993, 105.750190178381),
    "LOC-11": (9.99901844880748, 105.759600138197),
    "LOC-12": (10.0322030951477, 105.782015929596),
    "LOC-13": (10.0469330403007, 105.768429826955),
    "LOC-14": (10.0493279700204, 105.79067783787),
    "LOC-15": (10.0257054049919, 105.780764935446),
    "LOC-16": (10.005064478056, 105.723095321974),
    "LOC-17": (9.99707635523424, 105.782092809812),
    "LOC-18": (10.0218333103195, 105.760929763349),
    "LOC-19": (10.0125322348713, 105.732560730039),
    "LOC-20": (10.0284425326508, 105.77883702198),
}

# High's provided per-station counts sum to 67; the benchmark intentionally uses 67.
SCENARIOS = [
    {"name": "CTU-Low", "service_date": "2026-11-09", "demand": {
        "LOC-04": 5, "LOC-05": 5, "LOC-06": 4, "LOC-08": 4, "LOC-12": 3, "LOC-18": 3}},
    {"name": "CTU-Medium", "service_date": "2026-11-10", "demand": {
        "LOC-02": 8, "LOC-03": 7, "LOC-04": 6, "LOC-05": 6, "LOC-06": 5,
        "LOC-08": 5, "LOC-09": 4, "LOC-12": 4, "LOC-15": 3}},
    {"name": "CTU-High", "service_date": "2026-11-11", "demand": {
        "LOC-02": 8, "LOC-03": 7, "LOC-04": 6, "LOC-05": 6, "LOC-06": 6,
        "LOC-07": 5, "LOC-08": 5, "LOC-09": 5, "LOC-10": 4, "LOC-11": 4,
        "LOC-12": 4, "LOC-13": 3, "LOC-14": 2, "LOC-15": 2}},
    {"name": "CTU-Concentrated", "service_date": "2026-11-12", "demand": {
        "LOC-08": 16, "LOC-04": 14, "LOC-18": 10, "LOC-05": 6,
        "LOC-06": 5, "LOC-15": 4, "LOC-20": 3, "LOC-12": 2}},
    {"name": "CTU-Dispersed", "service_date": "2026-11-13", "demand": {
        "LOC-02": 4, "LOC-03": 4, "LOC-04": 4, "LOC-05": 4, "LOC-06": 4,
        "LOC-07": 4, "LOC-08": 4, "LOC-09": 4, "LOC-10": 4, "LOC-11": 4,
        "LOC-12": 4, "LOC-13": 4, "LOC-14": 3, "LOC-15": 3, "LOC-16": 3,
        "LOC-17": 3, "LOC-18": 3, "LOC-19": 3}},
]

# Mirrors current backend operating settings. Vehicles have DB capacity 30, but
# production presently clamps route capacity to 29.
MAX_CAPACITY_PER_VEHICLE = 29
MAX_SERVICE_RADIUS_KM = 10.0
MAX_DRIVING_MINUTES = 90.0
MORNING_SPEED_KMH = 25.0
DEPARTURE_MINUTES = 330.0  # 05:30
SCHOOL_DEADLINE_MINUTES = 410.0  # 06:50 (10 minutes before 07:00 class)
PICKUP_SERVICE_MINUTES = 3.0
STATION_WINDOW_MINUTES = 45.0


def haversine(a, b):
    radius = 6371.0
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def hhmm(minutes):
    value = int(minutes) % (24 * 60)
    return f"{value // 60:02d}:{value % 60:02d}"


def build_case(scenario):
    demand = scenario["demand"]
    if len(demand) > 100 or sum(demand.values()) > 100:
        raise ValueError(f"{scenario['name']}: station/ticket limit exceeded")
    stations = []
    for index, (code, count) in enumerate(demand.items()):
        if code not in LOCATIONS:
            raise ValueError(f"Unknown station code: {code}")
        coord = LOCATIONS[code]
        radius = haversine((DEPOT["lat"], DEPOT["lng"]), coord)
        if radius > MAX_SERVICE_RADIUS_KM:
            raise ValueError(f"{code} outside service radius: {radius:.2f} km")
        stations.append({
            "id": f"station_{index}", "location_code": code,
            "location_id": location_id_for(code), "lat": coord[0], "lng": coord[1],
            "demand": int(count), "radius_km": round(radius, 3),
        })
    total = sum(s["demand"] for s in stations)
    capacities = [min(v["database_capacity"], MAX_CAPACITY_PER_VEHICLE) for v in VEHICLES]
    if total > sum(capacities):
        raise ValueError(f"{scenario['name']}: {total} tickets exceed effective capacity {sum(capacities)}")

    points = [(DEPOT["lat"], DEPOT["lng"])] + [(s["lat"], s["lng"]) for s in stations]
    n = len(points)
    distances = [[0.0] * n for _ in range(n)]
    times = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                distances[i][j] = round(haversine(points[i], points[j]), 3)
                times[i][j] = round(distances[i][j] / MORNING_SPEED_KMH * 60.0, 2)
    for i, station in enumerate(stations, start=1):
        latest = SCHOOL_DEADLINE_MINUTES - times[i][0] - PICKUP_SERVICE_MINUTES
        station["time_window_start"] = hhmm(latest - STATION_WINDOW_MINUTES)
        station["time_window_end"] = hhmm(latest)
        station["matrix_index"] = i
    return stations, capacities, distances, times


def location_id_for(code):
    # IDs are embedded to make the file independently runnable and its inputs auditable.
    return LOCATION_IDS[code]


LOCATION_IDS = {
    "LOC-02": "8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea",
    "LOC-03": "44ef2b46-d9d0-49ad-97ec-8453762a1ad1",
    "LOC-04": "040a181f-47a2-48d9-ac88-7fdb9fcde4b8",
    "LOC-05": "ecdbfc40-6060-417c-827a-f14d45bfbb5f",
    "LOC-06": "2e1fea7c-167a-4225-aca3-c2c32e9dd6b2",
    "LOC-07": "4a91a412-bd81-4387-b926-193a9b7e3fce",
    "LOC-08": "0d903c1d-1f69-45d4-a3a2-abda7d5b7624",
    "LOC-09": "dfae6291-3fe1-4e22-9ecd-b61ddcf46f9f",
    "LOC-10": "62c11d70-1bd4-418f-9e76-7330e39d1104",
    "LOC-11": "04c3c9bd-f6a3-4457-844c-55f167457f03",
    "LOC-12": "90e66df6-f68d-4576-92eb-0ae757236ff4",
    "LOC-13": "e427b31b-1817-4588-8d9e-2c71bff55450",
    "LOC-14": "2419d4bd-7644-49c5-824a-c08fdaaef7af",
    "LOC-15": "8e0b583e-cded-438c-9c0a-821ae871c03e",
    "LOC-16": "fef2753e-50ce-4799-9e9d-9b455e5e5c85",
    "LOC-17": "559e2794-6f40-4a71-910e-6f889076bfae",
    "LOC-18": "9914fc16-6de1-4d73-91ad-7bcf9abd7985",
    "LOC-19": "527fd1f5-32dd-4bd5-8aad-74e335d6708a",
    "LOC-20": "4f9f0c03-7e7c-4497-8cc4-deacb540da32",
}


def evaluate(routes, stations, capacities, distances, times):
    total_distance = total_travel = early = late = tw_late = 0.0
    cap_viol = duration_viol = school_viol = tw_viol = 0
    duration_excess = 0.0
    details = []
    for route_index, route in enumerate(routes):
        if not route:
            continue
        capacity = capacities[min(route_index, len(capacities) - 1)]
        load = 0
        current = DEPARTURE_MINUTES
        previous = 0
        route_distance = route_drive = 0.0
        for station in route:
            idx = station["matrix_index"]
            distance, drive = distances[previous][idx], times[previous][idx]
            route_distance += distance
            route_drive += drive
            current += drive
            load += station["demand"]
            if load > capacity:
                cap_viol += 1
            start, end = map(parse_hhmm, (station["time_window_start"], station["time_window_end"]))
            if current < start:
                early += start - current
                current = start
            elif current > end:
                amount = current - end
                late += amount
                tw_late += amount
                tw_viol += 1
            current += PICKUP_SERVICE_MINUTES
            previous = idx
        route_distance += distances[previous][0]
        route_drive += times[previous][0]
        current += times[previous][0]
        total_distance += route_distance
        total_travel += route_drive
        if route_drive > MAX_DRIVING_MINUTES:
            duration_viol += 1
            duration_excess += route_drive - MAX_DRIVING_MINUTES
        if current > SCHOOL_DEADLINE_MINUTES:
            school_viol += 1
            late += current - SCHOOL_DEADLINE_MINUTES
        details.append({
            "station_codes": [s["location_code"] for s in route],
            "passenger_count": sum(s["demand"] for s in route),
            "drive_minutes": round(route_drive, 2),
            "distance_km": round(route_distance, 3),
            "school_arrival": hhmm(current),
        })
    # Same weights/formula as production SolutionEvaluator for pickup routing.
    early_penalty = early * 0.5
    late_penalty = late * 10.0
    tw_penalty = tw_late * 10000.0
    capacity_penalty = cap_viol * 1000.0
    duration_penalty = duration_excess * 10000.0
    school_penalty = school_viol * 10000.0
    objective = total_distance + early_penalty + late_penalty + tw_penalty + capacity_penalty + duration_penalty + school_penalty
    feasible = not (cap_viol or duration_viol or school_viol or tw_viol)
    metrics = {
        "objective_value": round(objective, 2),
        "total_distance_km": round(total_distance, 3),
        "total_travel_time_min": round(total_travel, 2),
        "early_arrival_min": round(early, 2),
        "late_arrival_min": round(late, 2),
        "time_window_violations": tw_viol,
        "capacity_violations": cap_viol,
        "route_duration_violations": duration_viol,
        "school_arrival_violations": school_viol,
        "is_feasible": feasible,
        "routes": details,
    }
    return objective, metrics


def parse_hhmm(value):
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def sweep_initial(stations, capacities):
    ordered = sorted(stations, key=lambda s: math.atan2(s["lat"] - DEPOT["lat"], s["lng"] - DEPOT["lng"]) % (2 * math.pi))
    routes, current, load, vehicle_index = [], [], 0, 0
    for station in ordered:
        capacity = capacities[min(vehicle_index, len(capacities) - 1)]
        projected = current + [station]
        # Production Sweep estimates driving duration at 30 km/h.
        points = [(DEPOT["lat"], DEPOT["lng"])] + [(s["lat"], s["lng"]) for s in projected]
        duration = sum(haversine(points[i], points[i + 1]) for i in range(len(points) - 1))
        duration += haversine(points[-1], points[0])
        duration = duration / 30.0 * 60.0
        if current and (load + station["demand"] > capacity or duration > MAX_DRIVING_MINUTES):
            routes.append(current)
            current, load, vehicle_index = [], 0, vehicle_index + 1
        current.append(station)
        load += station["demand"]
    if current:
        routes.append(current)
    if sum(s["demand"] for s in stations) >= 60 and len(routes) < 2 and len(capacities) >= 2:
        route = routes[0]
        middle = len(route) // 2
        routes = [route[:middle], route[middle:]]
    if len(routes) > len(capacities):
        raise ValueError(f"Sweep needs {len(routes)} vehicles; only {len(capacities)} are listed")
    return routes


class ALNS:
    def __init__(self, stations, capacities, distances, times, iterations=300, seed=42):
        self.stations, self.capacities = stations, capacities
        self.distances, self.times = distances, times
        self.iterations, self.rng = iterations, random.Random(seed)

    def _score(self, routes):
        return evaluate(routes, self.stations, self.capacities, self.distances, self.times)[0]

    def _remove_random(self, routes, count):
        result = copy.deepcopy(routes)
        positions = [(ri, si) for ri, route in enumerate(result) for si in range(len(route))]
        chosen = sorted(self.rng.sample(positions, min(count, len(positions))), reverse=True)
        removed = [result[ri].pop(si) for ri, si in chosen]
        return result, removed

    def _remove_worst(self, routes, count):
        result, removed = copy.deepcopy(routes), []
        for _ in range(min(count, sum(len(r) for r in result))):
            base, choice = self._score(result), None
            saving = float("-inf")
            for ri, route in enumerate(result):
                if len(route) < 2:
                    continue
                for si in range(len(route)):
                    candidate = copy.deepcopy(result)
                    candidate[ri].pop(si)
                    value = base - self._score(candidate)
                    if value > saving:
                        saving, choice = value, (ri, si)
            if choice is None:
                break
            ri, si = choice
            removed.append(result[ri].pop(si))
        return result, removed

    def _insert(self, routes, removed, regret=False):
        result, pending = copy.deepcopy(routes), list(removed)
        if not regret:
            self.rng.shuffle(pending)
        while pending:
            selected = None
            best_route, best_value, best_regret = None, float("inf"), float("-inf")
            for pi, station in enumerate(pending):
                options = []
                for ri in range(len(result)):
                    for pos in range(len(result[ri]) + 1):
                        candidate = copy.deepcopy(result)
                        candidate[ri].insert(pos, station)
                        options.append((self._score(candidate), candidate))
                options.sort(key=lambda item: item[0])
                if not options:
                    options = [(0.0, result + [[station]])]
                regret_value = options[1][0] - options[0][0] if len(options) > 1 else float("inf")
                if not regret:
                    regret_value = -pi
                if regret_value > best_regret:
                    selected, best_route, best_value, best_regret = pi, options[0][1], options[0][0], regret_value
            result = best_route
            pending.pop(selected)
        return [r for r in result if r]

    def run(self, initial):
        current = copy.deepcopy(initial)
        current_value, best_value = self._score(current), self._score(current)
        best = copy.deepcopy(current)
        # Adaptive operator weights for 2 destroy x 2 repair operators.
        weights = [[1.0, 1.0], [1.0, 1.0]]
        rewards = [[0.0, 0.0], [0.0, 0.0]]
        uses = [[0, 0], [0, 0]]
        temperature = max(1.0, current_value * 0.02)
        total = sum(s["demand"] for s in self.stations)
        for iteration in range(1, self.iterations + 1):
            destroy = self.rng.choices((0, 1), weights=(sum(weights[0]), sum(weights[1])))[0]
            repair = self.rng.choices((0, 1), weights=weights[destroy])[0]
            count = max(1, min(total - 1, round(self.rng.uniform(0.12, 0.30) * total)))
            partial, removed = self._remove_random(current, count) if destroy == 0 else self._remove_worst(current, count)
            candidate = self._insert(partial, removed, regret=bool(repair))
            value = self._score(candidate)
            uses[destroy][repair] += 1
            accepted = value < current_value or self.rng.random() < math.exp(-min(max(0.0, value-current_value) / max(temperature, 1e-9), 700.0))
            if accepted:
                current, current_value = candidate, value
                rewards[destroy][repair] += 1.0
            if value < best_value:
                best, best_value = copy.deepcopy(candidate), value
                rewards[destroy][repair] += 5.0
            temperature *= 0.995
            if iteration % 25 == 0:
                for di in range(2):
                    for ri in range(2):
                        if uses[di][ri]:
                            weights[di][ri] = max(0.05, 0.8 * weights[di][ri] + 0.2 * rewards[di][ri] / uses[di][ri])
                        rewards[di][ri] = uses[di][ri] = 0
        return best


def feasibility_rank(metrics):
    violations = sum(metrics[k] for k in (
        "capacity_violations", "route_duration_violations", "school_arrival_violations", "time_window_violations"))
    return (violations, metrics["capacity_violations"], metrics["route_duration_violations"],
            metrics["school_arrival_violations"], metrics["time_window_violations"], metrics["objective_value"])


def optimize_with_splits(routes, alns, stations, capacities, distances, times):
    best = alns.run(routes)
    _, metrics = evaluate(best, stations, capacities, distances, times)
    while not metrics["is_feasible"] and len(best) < len(capacities):
        best_split, best_rank = None, feasibility_rank(metrics)
        for ri, route in enumerate(best):
            for split in range(1, len(route)):
                candidate = copy.deepcopy(best)
                candidate[ri:ri+1] = [route[:split], route[split:]]
                _, candidate_metrics = evaluate(candidate, stations, capacities, distances, times)
                rank = feasibility_rank(candidate_metrics)
                if rank < best_rank:
                    best_split, best_rank = candidate, rank
        if best_split is None:
            break
        best = alns.run(best_split)
        _, metrics = evaluate(best, stations, capacities, distances, times)
    return best


def run(iterations, runs, seed):
    results = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        stations, capacities, distances, times = build_case(scenario)
        initial = sweep_initial(stations, capacities)
        _, baseline = evaluate(initial, stations, capacities, distances, times)
        run_rows = []
        for run_index in range(runs):
            run_seed = seed + scenario_index * 1000 + run_index
            solver = ALNS(stations, capacities, distances, times, iterations, run_seed)
            started = time.perf_counter()
            routes = optimize_with_splits(initial, solver, stations, capacities, distances, times)
            runtime = (time.perf_counter() - started) * 1000.0
            _, metrics = evaluate(routes, stations, capacities, distances, times)
            run_rows.append({"seed": run_seed, "runtime_ms": round(runtime, 2), **metrics})
        best = min(run_rows, key=feasibility_rank)
        results.append({
            "name": scenario["name"], "service_date": scenario["service_date"],
            "session_id": SESSION_ID, "trip_type": TRIP_TYPE,
            "station_count": len(stations), "ticket_count": sum(s["demand"] for s in stations),
            "depot": {"location_id": DEPOT["location_id"], "latitude": DEPOT["lat"], "longitude": DEPOT["lng"]},
            "vehicles": [{"id": v["id"], "database_capacity": v["database_capacity"],
                          "effective_capacity": capacities[i]} for i, v in enumerate(VEHICLES)],
            "stations": [{k: s[k] for k in ("location_id", "location_code", "lat", "lng", "demand", "time_window_start", "time_window_end", "radius_km")} for s in stations],
            "distance_model": "Haversine at 25 km/h morning speed; no road/traffic API",
            "time_window_model": "Same session-derived pickup windows as production backend",
            "production_capacity_limit": MAX_CAPACITY_PER_VEHICLE,
            "sweep_initial": baseline,
            "alns": {
                "iterations": iterations, "runs": runs,
                "runtime_ms_mean": round(statistics.mean(r["runtime_ms"] for r in run_rows), 2),
                "objective_mean": round(statistics.mean(r["objective_value"] for r in run_rows), 2),
                "objective_stddev": round(statistics.stdev(r["objective_value"] for r in run_rows), 2) if runs > 1 else 0.0,
                "best_run": best,
            },
        })
    return {
        "benchmark": "standalone CTU ALNS",
        "note": "No database reads/writes; no student or ticket identifiers are used.",
        "objective": "Production pickup SolutionEvaluator Z weights and penalties",
        "scenarios": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON results path")
    args = parser.parse_args()
    if args.iterations <= 0 or args.runs <= 0:
        parser.error("--iterations and --runs must be positive")
    result = run(args.iterations, args.runs, args.seed)
    summary = [{
        "scenario": s["name"], "tickets": s["ticket_count"],
        "sweep_Z": s["sweep_initial"]["objective_value"],
        "alns_Z": s["alns"]["best_run"]["objective_value"],
        "feasible": s["alns"]["best_run"]["is_feasible"],
        "runtime_ms_mean": s["alns"]["runtime_ms_mean"],
    } for s in result["scenarios"]]
    print(json.dumps(summary, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nDetailed results saved to {args.output}")


if __name__ == "__main__":
    main()
