"""Transform an immutable Solomon input into a reverse-pickup instance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .solomon_parser import SolomonInstance


def _reverse_node(node: Any, horizon: int, *, is_depot: bool = False) -> dict[str, Any]:
    ready = horizon - (node.due_date + node.service_time)
    due = horizon - (node.ready_time + node.service_time)
    if not 0 <= ready <= due <= horizon:
        raise ValueError(f"Invalid reverse window for customer {node.customer_id}: [{ready}, {due}]")
    return {
        "id": "DEPOT" if is_depot else f"customer_{node.customer_id}",
        "source_customer_id": node.customer_id,
        "name": "School Depot" if is_depot else f"Reverse Pickup Station {node.customer_id}",
        "x": node.x,
        "y": node.y,
        "demand": node.demand,
        "time_window_start": ready,
        "time_window_end": due,
        "service_time": node.service_time,
        "source_time_window_start": node.ready_time,
        "source_time_window_end": node.due_date,
    }


def transform_reverse_pickup(instance: SolomonInstance) -> dict[str, Any]:
    """Create the documented time-reversal variant; coordinates and demand stay intact."""
    horizon = instance.depot.due_date
    depot = _reverse_node(instance.depot, horizon, is_depot=True)
    stations = [_reverse_node(customer, horizon) for customer in instance.customers]
    return {
        "schema_version": "1.0",
        "dataset_type": "solomon_reverse_pickup",
        "source_instance": instance.name,
        "source_file": str(instance.source_path).replace("\\", "/"),
        "transform": {
            "planning_horizon": horizon,
            "time_window_rule": "ready=H-(source_due+service); due=H-(source_ready+service)",
            "demand_interpretation": "students_waiting_at_station",
            "route_semantics": "pickup_to_depot",
            "distance_metric": "euclidean",
            "travel_time_rule": "travel_time_equals_euclidean_distance",
        },
        "fleet": {"max_vehicles": instance.vehicle_count, "vehicle_capacity": instance.vehicle_capacity},
        "depot": depot,
        "stations": stations,
    }


def write_reverse_pickup(instance: SolomonInstance, output_path: str | Path) -> dict[str, Any]:
    payload = transform_reverse_pickup(instance)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
