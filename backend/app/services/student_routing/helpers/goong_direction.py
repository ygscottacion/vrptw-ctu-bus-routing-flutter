import json
import time
import logging
import urllib.request
import urllib.error
from threading import Lock
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.services.student_routing.helpers.goong_metrics import goong_metrics

logger = logging.getLogger(__name__)


def decode_polyline(polyline_str: str) -> List[List[float]]:
    """Decodes an Encoded Polyline string into a list of [lat, lng] pairs."""
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'lat': 0, 'lng': 0}

    while index < len(polyline_str):
        for unit in ['lat', 'lng']:
            shift, result = 0, 0
            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if byte < 0x20:
                    break
            if result & 1:
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)

        lat += changes['lat']
        lng += changes['lng']
        coordinates.append([round(lat / 1e5, 6), round(lng / 1e5, 6)])

    return coordinates


class GoongDirectionService:
    """
    Service gọi Goong Direction API, parse polyline, distance, duration
    và hỗ trợ caching TTL 24h với tọa độ làm tròn 5 chữ số thập phân.
    """

    def __init__(self, ttl_seconds: int = 86400):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._lock = Lock()

    def _build_cache_key(self, waypoints: List[Tuple[float, float]]) -> str:
        # Làm tròn 5 chữ số thập phân (~1m precision) để tối ưu cache hit
        coords_str = ";".join([f"{round(lat, 5)},{round(lng, 5)}" for lat, lng in waypoints])
        return f"polyline:{coords_str}"

    def get_route_polyline(
        self,
        waypoints: List[Tuple[float, float]],
        vehicle: str = "car"
    ) -> Dict[str, Any]:
        if len(waypoints) < 2:
            return {
                "encoded_polyline": "",
                "distance_km": 0.0,
                "duration_minutes": 0.0,
                "points": [[lat, lng] for lat, lng in waypoints],
                "cached": False,
                "cached_at": None,
            }

        cache_key = self._build_cache_key(waypoints)
        now = time.time()
        summary_str = f"origin={waypoints[0]},dest={waypoints[-1]}"

        # 1. Check cache hit
        with self._lock:
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if now - timestamp < self.ttl_seconds:
                    res = dict(cached_data)
                    res["cached"] = True
                    goong_metrics.log_goong_call("direction", summary_str, 0.0, 200, cache_hit=True)
                    return res

        # 2. Cache miss -> Call Goong Direction API
        api_key = settings.GOONG_API_KEY
        base_url = settings.GOONG_DIRECTION_BASE_URL.rstrip('/')

        if not api_key or api_key.startswith("your-"):
            logger.warning("GOONG_API_KEY unconfigured. Returning straight-line polyline fallback.")
            goong_metrics.log_goong_call("direction", summary_str, 0.0, 500, cache_hit=False, error="GOONG_API_KEY unconfigured")
            return {
                "encoded_polyline": "",
                "distance_km": 0.0,
                "duration_minutes": 0.0,
                "points": [[lat, lng] for lat, lng in waypoints],
                "cached": False,
                "cached_at": None,
            }

        origin_str = f"{waypoints[0][0]},{waypoints[0][1]}"
        dest_str = f"{waypoints[-1][0]},{waypoints[-1][1]}"
        url = f"{base_url}?origin={origin_str}&destination={dest_str}&vehicle={vehicle}&api_key={api_key}"

        if len(waypoints) > 2:
            middle_pts = "|".join([f"{lat},{lng}" for lat, lng in waypoints[1:-1]])
            url += f"&waypoints={middle_pts}"

        start_time = time.time()
        status_code = 500
        error_msg = None

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CTUBusRouting/2.0"})
            with urllib.request.urlopen(req, timeout=5.0) as response:
                status_code = response.status
                latency = (time.time() - start_time) * 1000.0

                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    routes = data.get("routes", [])
                    if routes:
                        first_route = routes[0]
                        overview_polyline = first_route.get("overview_polyline", {}).get("points", "")
                        legs = first_route.get("legs", [])

                        total_dist_m = sum(leg.get("distance", {}).get("value", 0) for leg in legs)
                        total_dur_s = sum(leg.get("duration", {}).get("value", 0) for leg in legs)

                        dist_km = round(total_dist_m / 1000.0, 3)
                        dur_mins = round(total_dur_s / 60.0, 2)

                        # Validate ETA anomaly
                        goong_metrics.validate_eta_anomaly(dist_km, dur_mins, summary_str)

                        decoded_pts = decode_polyline(overview_polyline) if overview_polyline else [[lat, lng] for lat, lng in waypoints]

                        result = {
                            "encoded_polyline": overview_polyline,
                            "distance_km": dist_km,
                            "duration_minutes": dur_mins,
                            "points": decoded_pts,
                            "cached": False,
                            "cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                        }

                        # Save to cache
                        with self._lock:
                            self._cache[cache_key] = (result, now)

                        goong_metrics.log_goong_call("direction", summary_str, latency, 200, cache_hit=False)
                        return result
                    else:
                        error_msg = "Goong Direction returned empty routes array"
        except urllib.error.HTTPError as e:
            status_code = e.code
            error_msg = f"HTTPError {e.code}: {e.reason}"
        except Exception as e:
            error_msg = f"Request failed: {e}"

        latency = (time.time() - start_time) * 1000.0
        goong_metrics.log_goong_call("direction", summary_str, latency, status_code, cache_hit=False, error=error_msg)

        # Fallback if API fails
        return {
            "encoded_polyline": "",
            "distance_km": 0.0,
            "duration_minutes": 0.0,
            "points": [[lat, lng] for lat, lng in waypoints],
            "cached": False,
            "cached_at": None,
        }

    def get_direction(
        self,
        origin: Dict[str, float],
        destination: Dict[str, float],
        vehicle: str = "car"
    ) -> Dict[str, Any]:
        """Direct call to Goong Direction API returning raw routes dict for snap-to-road checks."""
        api_key = settings.GOONG_API_KEY
        base_url = settings.GOONG_DIRECTION_BASE_URL.rstrip('/')
        url = f"{base_url}?origin={origin['lat']},{origin['lng']}&destination={destination['lat']},{destination['lng']}&vehicle={vehicle}&api_key={api_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "CTUBusRouting/2.0"})
        with urllib.request.urlopen(req, timeout=5.0) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
        return {}


# Global singleton & Provider class alias
goong_direction_service = GoongDirectionService()
GoongDirectionProvider = GoongDirectionService
