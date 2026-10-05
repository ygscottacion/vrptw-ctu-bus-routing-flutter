import uuid
from types import SimpleNamespace

from app.models.ticket import TicketStatus
from app.services.route_validator import RouteValidator


def test_persisted_route_allows_multiple_tickets_at_same_pickup_station():
    depot_id, station_id, route_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    route = SimpleNamespace(
        id=route_id,
        passenger_count=2,
        driving_duration_minutes=20.0,
        trip_type="pickup",
        session_id="MORNING_1",
        estimated_school_arrival_time=None,
    )
    stops = [
        SimpleNamespace(location_id=depot_id, stop_order=1),
        SimpleNamespace(
            location_id=station_id,
            stop_order=2,
            arrival_time=None,
            time_window_start=None,
            time_window_end=None,
        ),
    ]
    tickets = [
        SimpleNamespace(
            id=uuid.uuid4(),
            pickup_location_id=station_id,
            status=TicketStatus.ASSIGNED,
            route=route,
        )
        for _ in range(2)
    ]

    RouteValidator.validate_persisted_routes(
        created_routes=[(route, stops, tickets)],
        expected_tickets_count=2,
        depot_location_id=depot_id,
    )
