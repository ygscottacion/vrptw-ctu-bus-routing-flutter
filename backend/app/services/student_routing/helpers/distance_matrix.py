import math
import logging
import urllib.request
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from app.services.student_routing import config
from app.services.student_routing.helpers.path_flexibility import PathFlexibilityManager

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


class OSRMWithFallbackProvider(DistanceMatrixProvider):
    """
    Provider tích hợp OSRM Public API với timeout 3s và fallback sang Static Matrix khi bị lỗi / timeout.
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
