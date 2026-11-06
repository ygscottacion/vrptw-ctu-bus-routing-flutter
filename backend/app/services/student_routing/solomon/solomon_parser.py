"""Parser for the original Solomon 100-customer VRPTW text format."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SolomonCustomer:
    customer_id: int
    x: float
    y: float
    demand: int
    ready_time: int
    due_date: int
    service_time: int


@dataclass(frozen=True)
class SolomonInstance:
    name: str
    vehicle_count: int
    vehicle_capacity: int
    depot: SolomonCustomer
    customers: tuple[SolomonCustomer, ...]
    source_path: Path


def _data_lines(lines: Iterable[str]) -> list[list[str]]:
    """Return only seven-column customer records from a Solomon file."""
    records: list[list[str]] = []
    for line in lines:
        parts = line.split()
        if len(parts) == 7 and all(part.lstrip("+-").replace(".", "", 1).isdigit() for part in parts):
            records.append(parts)
    return records


def parse_solomon_instance(path: str | Path) -> SolomonInstance:
    """Parse a standard Solomon instance without modifying its source file."""
    source_path = Path(path)
    lines = source_path.read_text(encoding="utf-8").splitlines()
    non_empty = [line.strip() for line in lines if line.strip()]
    if not non_empty:
        raise ValueError(f"Solomon instance is empty: {source_path}")

    try:
        vehicle_header = next(index for index, line in enumerate(lines) if line.strip().upper() == "VEHICLE")
        customer_header = next(index for index, line in enumerate(lines) if line.strip().upper() == "CUSTOMER")
    except StopIteration as exc:
        raise ValueError(f"Invalid Solomon format (missing VEHICLE or CUSTOMER): {source_path}") from exc

    vehicle_records = [
        line.split() for line in lines[vehicle_header + 1:customer_header]
        if len(line.split()) == 2 and all(part.lstrip("+-").isdigit() for part in line.split())
    ]
    customer_records = _data_lines(lines[customer_header + 1:])
    if len(vehicle_records) != 1:
        raise ValueError(f"Expected one NUMBER/CAPACITY record in {source_path}")
    if len(customer_records) != 101:
        raise ValueError(f"Expected depot plus 100 customers in {source_path}, got {len(customer_records)}")

    vehicle_count, vehicle_capacity = map(int, vehicle_records[0])
    nodes = tuple(
        SolomonCustomer(
            customer_id=int(parts[0]), x=float(parts[1]), y=float(parts[2]), demand=int(parts[3]),
            ready_time=int(parts[4]), due_date=int(parts[5]), service_time=int(parts[6]),
        )
        for parts in customer_records
    )
    if nodes[0].customer_id != 0:
        raise ValueError(f"First customer must be depot 0 in {source_path}")
    if [node.customer_id for node in nodes] != list(range(101)):
        raise ValueError(f"Customer IDs must be contiguous 0..100 in {source_path}")

    return SolomonInstance(
        name=non_empty[0].upper(), vehicle_count=vehicle_count, vehicle_capacity=vehicle_capacity,
        depot=nodes[0], customers=nodes[1:], source_path=source_path,
    )
