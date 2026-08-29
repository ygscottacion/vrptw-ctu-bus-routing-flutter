import unittest
from app.services.demand_adapter import (
    DemandAdapter,
    RoutingValidationError,
    NoDemandError,
    NoVehicleAvailableError,
    InsufficientCapacityError,
    InvalidStationError,
)
from app.services.vrptw_solver import VRPTWSolverService
from app.services.student_routing.schemas import SessionId, TripType


class TestDemandAdapter(unittest.TestCase):

    def setUp(self):
        self.depot = {
            "id": "SCHOOL",
            "name": "Đại học Cần Thơ",
            "latitude": 10.0302,
            "longitude": 105.7721,
        }
        self.stations = [
            {
                "id": 1,
                "name": "Trạm Bến Ninh Kiều",
                "latitude": 10.0342,
                "longitude": 105.7876,
                "time_window_start": "06:00",
                "time_window_end": "06:20",
            },
            {
                "id": 2,
                "name": "Trạm Cầu Đầu Sấu",
                "latitude": 10.0055,
                "longitude": 105.7578,
                "time_window_start": "06:10",
                "time_window_end": "06:30",
            },
        ]
        self.vehicles = [
            {"id": 1, "license_plate": "65B-001.01", "capacity": 20},
            {"id": 2, "license_plate": "65B-002.02", "capacity": 20},
        ]

    def test_aggregate_tickets_to_station_demands(self):
        tickets = [
            {"id": 101, "pickup_location_id": 1},
            {"id": 102, "pickup_location_id": 1},
            {"id": 103, "pickup_location_id": 2},
            {"id": 104, "station_id": 2},
            {"id": 105, "location_id": 2},
        ]
        demands = DemandAdapter.aggregate_tickets_to_station_demands(tickets)
        self.assertEqual(demands.get(1), 2)
        self.assertEqual(demands.get(2), 3)
        self.assertIsNone(demands.get(3))

    def test_validate_time_window(self):
        self.assertTrue(DemandAdapter.validate_time_window("06:00", "06:30"))
        self.assertTrue(DemandAdapter.validate_time_window(None, None))
        self.assertFalse(DemandAdapter.validate_time_window("06:30", "06:00"))
        self.assertFalse(DemandAdapter.validate_time_window("25:00", "06:00"))
        self.assertFalse(DemandAdapter.validate_time_window("invalid", "06:00"))

    def test_validate_inputs_success(self):
        demands = {1: 5, 2: 10}
        depot_dict, locs_dict, vehs_dict = DemandAdapter.build_solver_inputs(
            depot=self.depot,
            stations=self.stations,
            vehicles=self.vehicles,
            station_demands=demands,
        )
        self.assertEqual(depot_dict["id"], "SCHOOL")
        self.assertEqual(len(locs_dict), 2)
        self.assertEqual(locs_dict[0]["demand"], 5)
        self.assertEqual(locs_dict[1]["demand"], 10)
        self.assertEqual(len(vehs_dict), 2)

    def test_validate_inputs_no_demand(self):
        demands = {}
        with self.assertRaises(NoDemandError):
            DemandAdapter.build_solver_inputs(
                depot=self.depot,
                stations=self.stations,
                vehicles=self.vehicles,
                station_demands=demands,
            )

    def test_validate_inputs_no_vehicles(self):
        demands = {1: 5}
        with self.assertRaises(NoVehicleAvailableError):
            DemandAdapter.build_solver_inputs(
                depot=self.depot,
                stations=self.stations,
                vehicles=[],
                station_demands=demands,
            )

    def test_validate_inputs_insufficient_capacity(self):
        demands = {1: 25, 2: 20}  # Total 45 > 40 total capacity
        with self.assertRaises(InsufficientCapacityError):
            DemandAdapter.build_solver_inputs(
                depot=self.depot,
                stations=self.stations,
                vehicles=self.vehicles,
                station_demands=demands,
            )

    def test_validate_inputs_invalid_station_coordinates(self):
        demands = {1: 5}
        bad_stations = [{
            "id": 1,
            "name": "Bad Lat",
            "latitude": 999.0,
            "longitude": 105.7,
            "time_window_start": "06:00",
            "time_window_end": "06:30",
        }]
        with self.assertRaises(InvalidStationError):
            DemandAdapter.build_solver_inputs(
                depot=self.depot,
                stations=bad_stations,
                vehicles=self.vehicles,
                station_demands=demands,
            )

    def test_validate_inputs_invalid_time_window(self):
        demands = {1: 5}
        bad_stations = [{
            "id": 1,
            "name": "Bad TW",
            "latitude": 10.03,
            "longitude": 105.7,
            "time_window_start": "07:00",
            "time_window_end": "06:00",
        }]
        with self.assertRaises(InvalidStationError):
            DemandAdapter.build_solver_inputs(
                depot=self.depot,
                stations=bad_stations,
                vehicles=self.vehicles,
                station_demands=demands,
            )

    def test_adapter_and_solver_end_to_end(self):
        tickets = [
            {"id": 1, "pickup_location_id": 1},
            {"id": 2, "pickup_location_id": 1},
            {"id": 3, "pickup_location_id": 2},
        ]
        demands = DemandAdapter.aggregate_tickets_to_station_demands(tickets)
        depot_dict, locs_dict, vehs_dict = DemandAdapter.build_solver_inputs(
            depot=self.depot,
            stations=self.stations,
            vehicles=self.vehicles,
            station_demands=demands,
        )

        solver = VRPTWSolverService()
        routes = solver.solve(
            depot=depot_dict,
            locations=locs_dict,
            vehicles=vehs_dict,
            session_id=SessionId.MORNING_1,
            trip_type=TripType.PICKUP,
        )

        self.assertIsInstance(routes, list)
        self.assertGreaterEqual(len(routes), 1)
        first_route = routes[0]
        self.assertIn("vehicle_id", first_route)
        self.assertIn("ordered_stops", first_route)
        self.assertIn("total_distance_km", first_route)


if __name__ == "__main__":
    unittest.main()
