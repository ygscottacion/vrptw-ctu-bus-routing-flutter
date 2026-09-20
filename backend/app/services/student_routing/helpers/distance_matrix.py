import math
import logging
import urllib.request
import urllib.error
import json
import time
import warnings
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from app.services.student_routing import config
from app.services.student_routing.helpers.path_flexibility import PathFlexibilityManager
from app.services.student_routing.helpers.goong_metrics import goong_metrics

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Tính khoảng cách Haversine giữa 2 tọa độ (km).
    """
    R = 6371.0  # Bán kính Trái Đất (km)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class DistanceMatrixProvider(ABC):
    """
    Interface trừu tượng cho Distance & Travel Time Matrix Provider.
    """

    @abstractmethod
    def get_matrix(
        self,
        points: List[Dict[str, float]],
        time_str_or_session: str = "MORNING_1"
    ) -> Tuple[List[List[float]], List[List[float]], str]:
        """
        Trả về:
            - distance_matrix (km)
            - travel_time_matrix (minutes)
            - source_used ("OSRM" hoặc "STATIC_FALLBACK")
        """
        pass


class StaticDistanceMatrixProvider(DistanceMatrixProvider):
    """
    Provider ma trận tĩnh: Sử dụng Haversine distance và tốc độ trung bình theo khung giờ từ PathFlexibilityManager.
    """

    def get_matrix(
        self,
        points: List[Dict[str, float]],
        time_str_or_session: str = "MORNING_1"
    ) -> Tuple[List[List[float]], List[List[float]], str]:
        n = len(points)
        speed_kmh = PathFlexibilityManager.get_average_speed_kmh(time_str_or_session)

        distance_matrix = [[0.0] * n for _ in range(n)]
        travel_time_matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    distance_matrix[i][j] = 0.0
                    travel_time_matrix[i][j] = 0.0
                else:
                    dist = haversine_distance(
                        points[i]["lat"], points[i]["lng"],
                        points[j]["lat"], points[j]["lng"]
                    )
                    distance_matrix[i][j] = round(dist, 3)
                    # Travel time in minutes = (dist / speed) * 60
                    travel_time_matrix[i][j] = round((dist / speed_kmh) * 60.0, 2)

        return distance_matrix, travel_time_matrix, "STATIC_FALLBACK"


import warnings
import urllib.error

def deprecated(reason: str):
    """Decorator to mark classes or functions as deprecated."""
    def decorator(cls_or_func):
        orig_init = getattr(cls_or_func, "__init__", None)
        if orig_init:
            def new_init(self, *args, **kwargs):
                warnings.warn(
                    f"{cls_or_func.__name__} is deprecated: {reason}",
                    DeprecationWarning,
                    stacklevel=2
                )
                orig_init(self, *args, **kwargs)
            cls_or_func.__init__ = new_init
        return cls_or_func
    return decorator


class GoongDistanceMatrixProvider(DistanceMatrixProvider):
    """
    Provider tích hợp Goong Distance Matrix API với fallback sang Static Matrix khi bị lỗi / timeout / missing key.
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        timeout: float = None
    ):
        self.api_key = api_key if api_key is not None else config.GOONG_API_KEY
        self.base_url = (base_url if base_url is not None else config.GOONG_DISTANCE_MATRIX_BASE_URL).rstrip('/')
        self.timeout = timeout if timeout is not None else config.GOONG_TIMEOUT_SECONDS
        self.static_provider = StaticDistanceMatrixProvider()

    def get_matrix(
        self,
        points: List[Dict[str, float]],
        time_str_or_session: str = "MORNING_1"
    ) -> Tuple[List[List[float]], List[List[float]], str]:
        if not points:
            return [], [], "STATIC_FALLBACK"

        if not self.api_key or self.api_key.startswith("your-"):
            goong_metrics.record_fallback("Missing or unconfigured GOONG_API_KEY")
            return self.static_provider.get_matrix(points, time_str_or_session)

        n = len(points)
        dist_matrix = [[0.0] * n for _ in range(n)]
        time_matrix = [[0.0] * n for _ in range(n)]

        # Goong Distance Matrix API limit: max 100 elements (origins * destinations <= 100)
        CHUNK_SIZE = 10
        summary = f"points_count={n}"
        start_time = time.time()
        status_code = 200
        error_msg = None

        try:
            for i in range(0, n, CHUNK_SIZE):
                orig_chunk = points[i:i + CHUNK_SIZE]
                orig_str = "|".join([f"{p['lat']},{p['lng']}" for p in orig_chunk])

                for j in range(0, n, CHUNK_SIZE):
                    dest_chunk = points[j:j + CHUNK_SIZE]
                    dest_str = "|".join([f"{p['lat']},{p['lng']}" for p in dest_chunk])

                    url = f"{self.base_url}?origins={orig_str}&destinations={dest_str}&vehicle=car&api_key={self.api_key}"
                    req = urllib.request.Request(url, headers={"User-Agent": "CTUBusRouting/2.0"})

                    with urllib.request.urlopen(req, timeout=self.timeout) as response:
                        if response.status != 200:
                            raise urllib.error.HTTPError(url, response.status, f"HTTP {response.status}", {}, None)

                        data = json.loads(response.read().decode("utf-8"))
                        rows = data.get("rows", [])

                        if len(rows) != len(orig_chunk):
                            raise ValueError(f"Response rows count mismatch: got {len(rows)}, expected {len(orig_chunk)}")

                        for r_idx, row in enumerate(rows):
                            elements = row.get("elements", [])
                            if len(elements) != len(dest_chunk):
                                raise ValueError(f"Element count mismatch in row {r_idx}: got {len(elements)}, expected {len(dest_chunk)}")

                            for c_idx, elem in enumerate(elements):
                                elem_status = elem.get("status", "OK")
                                if elem_status != "OK":
                                    raise ValueError(f"Goong Matrix element status error at ({i + r_idx},{j + c_idx}): {elem_status}")

                                val_m = elem.get("distance", {}).get("value", 0)
                                val_s = elem.get("duration", {}).get("value", 0)

                                row_i = i + r_idx
                                col_j = j + c_idx
                                dist_matrix[row_i][col_j] = round(val_m / 1000.0, 3)  # meters -> km
                                time_matrix[row_i][col_j] = round(val_s / 60.0, 2)    # seconds -> minutes

                                if row_i != col_j:
                                    goong_metrics.validate_eta_anomaly(
                                        dist_matrix[row_i][col_j],
                                        time_matrix[row_i][col_j],
                                        f"pt[{row_i}]->pt[{col_j}]"
                                    )

            latency = (time.time() - start_time) * 1000.0
            goong_metrics.log_goong_call("distance_matrix", summary, latency, 200, cache_hit=False)
            return dist_matrix, time_matrix, "GOONG"

        except urllib.error.HTTPError as e:
            status_code = e.code
            error_msg = f"HTTPError {e.code}: {e.reason}"
        except Exception as e:
            status_code = 500
            error_msg = f"Request failed: {e}"

        latency = (time.time() - start_time) * 1000.0
        goong_metrics.log_goong_call("distance_matrix", summary, latency, status_code, cache_hit=False, error=error_msg)
        goong_metrics.record_fallback(error_msg or f"HTTP {status_code}")

        # Fallback to static matrix if Goong API call failed, rate limited, or timed out
        return self.static_provider.get_matrix(points, time_str_or_session)



@deprecated("OSRM Public API is deprecated. Use GoongDistanceMatrixProvider instead.")
class OSRMWithFallbackProvider(DistanceMatrixProvider):
    """
    Provider tích hợp OSRM Public API với timeout 3s và fallback sang Static Matrix khi bị lỗi / timeout.
    @deprecated: Ưu tiên dùng GoongDistanceMatrixProvider.
    """

    def __init__(self, osrm_url: str = config.OSRM_PUBLIC_URL, timeout: float = config.OSRM_TIMEOUT_SECONDS):
        self.osrm_url = osrm_url
        self.timeout = timeout
        self.static_provider = StaticDistanceMatrixProvider()

    def get_matrix(
        self,
        points: List[Dict[str, float]],
        time_str_or_session: str = "MORNING_1"
    ) -> Tuple[List[List[float]], List[List[float]], str]:
        if not points:
            return [], [], "STATIC_FALLBACK"

        # Format coordinates for OSRM: lng,lat;lng,lat...
        coords_str = ";".join([f"{p['lng']},{p['lat']}" for p in points])
        url = f"{self.osrm_url}{coords_str}?annotations=distance,duration"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CTUBusRouting/2.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if data.get("code") == "Ok":
                        distances_m = data["distances"]
                        durations_s = data["durations"]

                        n = len(points)
                        dist_matrix = [[0.0] * n for _ in range(n)]
                        time_matrix = [[0.0] * n for _ in range(n)]

                        for i in range(n):
                            for j in range(n):
                                dist_matrix[i][j] = round(distances_m[i][j] / 1000.0, 3)  # m -> km
                                time_matrix[i][j] = round(durations_s[i][j] / 60.0, 2)    # s -> mins

                        return dist_matrix, time_matrix, "OSRM"
        except Exception as e:
            logger.warning(f"OSRM request failed/timed out after {self.timeout}s: {e}. Falling back to static matrix.")

        # Fallback to static matrix if OSRM call failed or timed out
        return self.static_provider.get_matrix(points, time_str_or_session)

