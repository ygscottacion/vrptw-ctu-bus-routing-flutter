"""
route_validator.py
==================
Module thẩm định tính hợp lệ của lộ trình xe buýt (Route Validator).
Được thiết kế cho vai trò của Khánh (Validation & Backend Job Lifecycle).

4 Quy tắc kiểm tra bắt buộc (Day 9 Contract):
1. `đủ stop` (Completeness): 100% trạm có nhu cầu / sinh viên được phân bổ, không bỏ sót.
2. `không lặp` (No Duplicate Stops): Không trùng lặp trạm trung gian trong lộ trình của xe.
3. `≤ 45 khách` (Capacity Constraint): Tải trọng mỗi xe tuyệt đối <= 45 khách.
4. `≤ 90 phút` (Max Route Duration): Thời lượng di chuyển toàn tuyến mỗi xe tuyệt đối <= 90 phút.
"""

import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


class RouteValidationError(Exception):
    """Ngoại lệ phát sinh khi lời giải hoặc cấu trúc tuyến vi phạm ràng buộc kỹ thuật."""

    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{error_code}] {message}")


def parse_time_to_minutes(time_val: Any) -> Optional[float]:
    """Chuyển đổi chuỗi 'HH:MM' hoặc datetime sang số phút trong ngày (0..1439)."""
    if time_val is None or time_val == "":
        return None
    if isinstance(time_val, (datetime.datetime, datetime.time)):
        return float(time_val.hour * 60 + time_val.minute)
    if isinstance(time_val, (int, float)):
        return float(time_val)
    try:
        parts = str(time_val).strip().split(":")
        if len(parts) >= 2:
            return float(int(parts[0]) * 60 + int(parts[1]))
    except Exception:
        pass
    return None


def calculate_stops_duration_minutes(ordered_stops: Sequence[Mapping[str, Any]]) -> Optional[float]:
    """
    Tính thời lượng hành trình (phút) giữa điểm dừng đầu tiên và điểm dừng cuối cùng.
    Hỗ trợ đọc từ `arrival_time` hoặc `departure_time`.
    """
    if not ordered_stops or len(ordered_stops) < 2:
        return 0.0

    first_time = None
    for stop in ordered_stops:
        t = parse_time_to_minutes(stop.get("departure_time") or stop.get("arrival_time"))
        if t is not None:
            first_time = t
            break

    last_time = None
    for stop in reversed(ordered_stops):
        t = parse_time_to_minutes(stop.get("arrival_time") or stop.get("departure_time"))
        if t is not None:
            last_time = t
            break

    if first_time is not None and last_time is not None:
        duration = last_time - first_time
        if duration < 0:
            duration += 1440.0  # Qua mốc nửa đêm
        return duration

    return None


class RouteValidator:
    """
    Service thẩm định lời giải phân cụm & tối ưu định tuyến.
    Đảm bảo 4 tiêu chí cốt lõi: ĐỦ STOP - KHÔNG LẶP - <= 45 KHÁCH - <= 90 PHÚT.
    """

    MAX_VEHICLE_CAPACITY: int = 45
    MAX_ROUTE_DURATION_MINUTES: float = 90.0

    @classmethod
    def validate_solver_routes(
        cls,
        routes: Sequence[Mapping[str, Any]],
        expected_station_ids: Optional[Set[Any]] = None,
        expected_total_demand: Optional[int] = None,
        max_capacity: int = 45,
        max_duration_minutes: float = 90.0,
    ) -> Dict[str, Any]:
        """
        Thẩm định dữ liệu đầu ra từ Solver (VRPTWSolverService / StudentRoutingService).

        Parameters
        ----------
        routes : Sequence[Mapping[str, Any]]
            Danh sách các tuyến xe từ solver, mỗi phần tử chứa:
            - `vehicle_id`: định danh xe
            - `total_demand`: tổng số khách chở
            - `ordered_stops`: danh sách các điểm dừng theo thứ tự
        expected_station_ids : Optional[Set[Any]]
            Tập hợp ID của các trạm cần phục vụ (phục vụ kiểm tra `đủ stop`).
        expected_total_demand : Optional[int]
            Tổng số vé/khách dự kiến (phục vụ kiểm tra `đủ stop`).
        max_capacity : int, default 45
            Sức chứa tối đa của mỗi xe buýt.
        max_duration_minutes : float, default 90.0
            Thời lượng hành trình tối đa của mỗi tuyến xe.

        Returns
        -------
        Dict[str, Any]
            Báo cáo thẩm định nếu tất cả các tiêu chí đều đạt.
        """
        if not routes:
            raise RouteValidationError(
                error_code="EMPTY_ROUTES",
                message="Thuật toán không trả về tuyến xe nào.",
            )

        visited_station_ids: Set[str] = set()
        total_served_demand = 0

        for r_idx, route in enumerate(routes):
            vehicle_id = str(route.get("vehicle_id", f"Route_{r_idx + 1}"))
            total_demand = int(route.get("total_demand", 0))
            stops = list(route.get("ordered_stops", []))

            # ── 1. Quy tắc: <= 45 khách (Chặn quá tải) ──
            if total_demand > max_capacity:
                raise RouteValidationError(
                    error_code="OVERLOAD_VIOLATION",
                    message=f"Tuyến xe {vehicle_id} chở {total_demand} khách, vượt quá sức chứa tối đa {max_capacity} chỗ.",
                    details={"vehicle_id": vehicle_id, "total_demand": total_demand, "max_capacity": max_capacity},
                )

            # ── 2. Quy tắc: Không lặp trạm trong cùng 1 tuyến ──
            route_intermediate_stops: List[str] = []
            for s_idx, stop in enumerate(stops):
                stop_id = str(stop.get("id", ""))
                if not stop_id:
                    raise RouteValidationError(
                        error_code="INVALID_ROUTE_STRUCTURE",
                        message=f"Tuyến xe {vehicle_id} chứa điểm dừng không có id hợp lệ: {stop!r}",
                        details={"vehicle_id": vehicle_id, "stop_index": s_idx},
                    )

                # Bỏ qua depot/SCHOOL ở đầu và cuối khi kiểm tra lặp trạm đón khách
                if stop_id in {"depot", "SCHOOL", "0"}:
                    continue

                if stop_id in route_intermediate_stops:
                    raise RouteValidationError(
                        error_code="DUPLICATE_STOPS",
                        message=f"Tuyến xe {vehicle_id} xuất hiện trạm trùng lặp: '{stop_id}'.",
                        details={"vehicle_id": vehicle_id, "duplicate_stop_id": stop_id},
                    )
                route_intermediate_stops.append(stop_id)
                visited_station_ids.add(stop_id)

            # ── 3. Quy tắc: <= 90 phút (Chặn quá giờ) ──
            duration = calculate_stops_duration_minutes(stops)
            # Nếu route có trường duration_minutes được cung cấp trực tiếp
            if duration is None and "duration_minutes" in route:
                duration = float(route["duration_minutes"])

            if duration is not None and duration > max_duration_minutes:
                raise RouteValidationError(
                    error_code="OVERTIME_VIOLATION",
                    message=f"Tuyến xe {vehicle_id} có thời lượng {duration:.1f} phút, vượt quá ngưỡng cho phép {max_duration_minutes} phút.",
                    details={"vehicle_id": vehicle_id, "duration_minutes": duration, "max_duration": max_duration_minutes},
                )

            total_served_demand += total_demand

        # ── 4. Quy tắc: Đủ stop (Không sót trạm, không sót khách) ──
        if expected_station_ids is not None:
            expected_clean = {str(sid) for sid in expected_station_ids if str(sid) not in {"depot", "SCHOOL", "0"}}
            missing_stations = expected_clean - visited_station_ids
            if missing_stations:
                raise RouteValidationError(
                    error_code="MISSING_STOPS",
                    message=f"Có {len(missing_stations)} trạm chưa được phân bổ vào lộ trình: {sorted(list(missing_stations))}",
                    details={"missing_stations": sorted(list(missing_stations))},
                )

        if expected_total_demand is not None and total_served_demand != expected_total_demand:
            raise RouteValidationError(
                error_code="DEMAND_MISMATCH",
                message=f"Tổng số sinh viên được phục vụ ({total_served_demand}) không khớp với nhu cầu dự kiến ({expected_total_demand}).",
                details={"served_demand": total_served_demand, "expected_demand": expected_total_demand},
            )

        return {
            "status": "VALID",
            "total_routes": len(routes),
            "total_served_demand": total_served_demand,
            "total_stations_visited": len(visited_station_ids),
            "max_capacity_complied": True,
            "max_duration_complied": True,
            "no_duplicates": True,
            "completeness_verified": True,
        }

    @classmethod
    def validate_persisted_routes(
        cls,
        created_routes: Sequence[Tuple[Any, Sequence[Any], Sequence[Any]]],
        expected_tickets_count: int,
        depot_location_id: Any,
        max_capacity: int = 45,
        max_duration_minutes: float = 90.0,
    ) -> None:
        """
        Thẩm định danh sách ORM Route, RouteStop, Ticket trước khi commit vào database trong route_worker.
        """
        if not created_routes:
            raise RouteValidationError(
                error_code="EMPTY_ROUTES",
                message="Không có tuyến xe nào được tạo.",
            )

        assigned_ticket_ids: Set[str] = set()
        actual_total_stops = 0
        depot_id_str = str(depot_location_id)

        for route, stops, tickets in created_routes:
            route_id_str = str(route.id)
            passenger_count = getattr(route, "passenger_count", len(tickets))

            # 1. <= 45 khách
            if passenger_count > max_capacity:
                raise RouteValidationError(
                    error_code="OVERLOAD_VIOLATION",
                    message=f"Tuyến {route_id_str} chở {passenger_count} khách, vượt quá giới hạn {max_capacity}.",
                    details={"route_id": route_id_str, "passenger_count": passenger_count},
                )

            # 2. Cấu trúc stops: stop[0] là depot, stop_order liên tục 1..N
            if not stops:
                raise RouteValidationError(
                    error_code="INVALID_ROUTE_STRUCTURE",
                    message=f"Tuyến {route_id_str} không có điểm dừng nào.",
                )

            if str(stops[0].location_id) != depot_id_str or stops[0].stop_order != 1:
                raise RouteValidationError(
                    error_code="INVALID_ROUTE_STRUCTURE",
                    message=f"Tuyến {route_id_str} không có trạm xuất phát hợp lệ tại điểm dừng số 1.",
                )

            if any(stop.stop_order != idx + 1 for idx, stop in enumerate(stops)):
                raise RouteValidationError(
                    error_code="INVALID_ROUTE_STRUCTURE",
                    message=f"Tuyến {route_id_str} có thứ tự điểm dừng không liên tục.",
                )

            # 3. Không lặp trạm đón trung gian
            pickup_ids = [str(stop.location_id) for stop in stops[1:]]
            if len(pickup_ids) != len(set(pickup_ids)):
                raise RouteValidationError(
                    error_code="DUPLICATE_STOPS",
                    message=f"Tuyến {route_id_str} có trạm đón bị trùng lặp.",
                    details={"route_id": route_id_str},
                )

            # 4. <= 90 phút (Kiểm tra duration giữa điểm dừng đầu và cuối nếu có arrival_time)
            first_arrival = stops[0].arrival_time
            last_arrival = stops[-1].arrival_time
            if first_arrival and last_arrival and isinstance(first_arrival, datetime.datetime) and isinstance(last_arrival, datetime.datetime):
                duration_m = (last_arrival - first_arrival).total_seconds() / 60.0
                if duration_m > max_duration_minutes:
                    raise RouteValidationError(
                        error_code="OVERTIME_VIOLATION",
                        message=f"Tuyến {route_id_str} có thời gian hành trình {duration_m:.1f} phút, vượt quá {max_duration_minutes} phút.",
                        details={"route_id": route_id_str, "duration_minutes": duration_m},
                    )

            # 5. Gán vé 1-1 chính xác
            ticket_loc_ids = [str(t.pickup_location_id) for t in tickets]
            if set(pickup_ids) != set(ticket_loc_ids) or len(ticket_loc_ids) != len(set(ticket_loc_ids)):
                raise RouteValidationError(
                    error_code="ROUTE_STOP_COUNT_MISMATCH",
                    message=f"Route {route_id_str} stops and tickets are not one-to-one.",
                )

            for t in tickets:
                st = getattr(t, "status", None)
                st_val = getattr(st, "value", str(st)).lower()
                if st_val != "assigned" or getattr(t, "route", None) is not route:
                    raise RouteValidationError(
                        error_code="UNASSIGNED_TICKET",
                        message=f"Route {route_id_str} contains an unassigned ticket.",
                    )

            actual_total_stops += len(stops)
            assigned_ticket_ids.update(str(t.id) for t in tickets)

        # 6. Đủ stop (Toàn bộ tickets đã gán không thừa không thiếu)
        if len(assigned_ticket_ids) != expected_tickets_count:
            raise RouteValidationError(
                error_code="MISSING_STOPS",
                message=f"Đã gán {len(assigned_ticket_ids)} / {expected_tickets_count} vé vào các tuyến.",
                details={"assigned": len(assigned_ticket_ids), "expected": expected_tickets_count},
            )

        if actual_total_stops != expected_tickets_count + len(created_routes):
            raise RouteValidationError(
                error_code="ROUTE_STOP_COUNT_MISMATCH",
                message="Tổng số điểm dừng không bằng số depot + số vé được phân bổ.",
            )
