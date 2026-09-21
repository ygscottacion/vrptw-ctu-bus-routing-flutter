import json
import time
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Any, Optional

logger = logging.getLogger("goong_monitoring")

# Daily Quota limit (default 10,000 requests/day, configurable)
DAILY_QUOTA_LIMIT = 10000


class GoongMetricsCollector:
    """
    Collector thu thập metrics, structured JSON logging và cảnh báo cho Goong API.
    """

    def __init__(self, quota_limit: int = DAILY_QUOTA_LIMIT):
        self.quota_limit = quota_limit
        self._lock = Lock()
        self._reset_daily_counters()

    def _reset_daily_counters(self):
        self._current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.metrics = {
            "total_requests": {"direction": 0, "distance_matrix": 0},
            "cache_hits": 0,
            "cache_misses": 0,
            "api_errors": {"timeout": 0, "401_403": 0, "429": 0, "5xx": 0, "other": 0},
            "fallback_to_static_count": 0,
            "anomalous_eta_count": 0,
            "daily_request_count": 0,
        }

    def _check_day_rollover(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._current_day:
            self._reset_daily_counters()

    def log_goong_call(
        self,
        endpoint: str,
        origin_dest_summary: str,
        latency_ms: float,
        status_code: int,
        cache_hit: bool = False,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ghi structured log (JSON) cho mỗi lần gọi Goong API và cập nhật metrics."""
        with self._lock:
            self._check_day_rollover()
            self.metrics["daily_request_count"] += 1
            if endpoint in self.metrics["total_requests"]:
                self.metrics["total_requests"][endpoint] += 1

            if cache_hit:
                self.metrics["cache_hits"] += 1
            else:
                self.metrics["cache_misses"] += 1

            if status_code != 200 or error:
                if status_code in (401, 403):
                    self.metrics["api_errors"]["401_403"] += 1
                elif status_code == 429:
                    self.metrics["api_errors"]["429"] += 1
                elif status_code >= 500:
                    self.metrics["api_errors"]["5xx"] += 1
                elif "timeout" in (error or "").lower():
                    self.metrics["api_errors"]["timeout"] += 1
                else:
                    self.metrics["api_errors"]["other"] += 1

            used_quota = self.metrics["daily_request_count"]
            quota_percentage = round((used_quota / self.quota_limit) * 100, 2)

            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "goong_maps",
                "endpoint": endpoint,
                "origin_destination": origin_dest_summary,
                "latency_ms": round(latency_ms, 2),
                "status_code": status_code,
                "cache_hit": cache_hit,
                "error": error,
                "daily_quota_used": used_quota,
                "daily_quota_percent": quota_percentage,
            }

            # Log formatted JSON string (Bảo mật: KHÔNG chứa GOONG_API_KEY)
            if status_code == 200 and not error:
                logger.info(json.dumps(log_entry))
            else:
                logger.error(json.dumps(log_entry))

            # Trigger alert warning if quota exceeds 80%
            if quota_percentage >= 80.0:
                logger.warning(
                    f"ALERT [QUOTA_NEAR_LIMIT]: Goong API quota reached {quota_percentage}% "
                    f"({used_quota}/{self.quota_limit} reqs today)."
                )

            return log_entry

    def record_fallback(self, reason: str):
        with self._lock:
            self._check_day_rollover()
            self.metrics["fallback_to_static_count"] += 1
            logger.warning(f"ALERT [FALLBACK_TRIGGERED]: Fallback to StaticDistanceMatrixProvider. Reason: {reason}")

    def validate_eta_anomaly(
        self,
        distance_km: float,
        duration_minutes: float,
        origin_dest_summary: str
    ) -> Optional[str]:
        """
        Kiểm tra ETA bất thường: âm, bằng 0 (khi khoảng cách > 100m), hoặc vận tốc > 150 km/h hay < 2 km/h.
        """
        if distance_km <= 0.1:
            return None  # Điểm trùng hoặc rất gần

        if duration_minutes <= 0:
            msg = f"ALERT [ETA_ANOMALY]: Invalid duration ({duration_minutes} mins) for distance {distance_km} km at {origin_dest_summary}"
            with self._lock:
                self.metrics["anomalous_eta_count"] += 1
            logger.warning(msg)
            return msg

        # Tính vận tốc trung bình (km/h)
        speed_kmh = (distance_km / (duration_minutes / 60.0))

        if speed_kmh > 150.0:
            msg = f"ALERT [ETA_ANOMALY]: Unrealistic high speed ({speed_kmh:.1f} km/h > 150 km/h) for dist {distance_km}km in {duration_minutes}m at {origin_dest_summary}"
            with self._lock:
                self.metrics["anomalous_eta_count"] += 1
            logger.warning(msg)
            return msg
        elif speed_kmh < 2.0:
            msg = f"ALERT [ETA_ANOMALY]: Unrealistic slow speed ({speed_kmh:.1f} km/h < 2 km/h) for dist {distance_km}km in {duration_minutes}m at {origin_dest_summary}"
            with self._lock:
                self.metrics["anomalous_eta_count"] += 1
            logger.warning(msg)
            return msg

        return None

    def get_metrics_summary(self) -> Dict[str, Any]:
        with self._lock:
            self._check_day_rollover()
            total_cache_reqs = self.metrics["cache_hits"] + self.metrics["cache_misses"]
            cache_hit_rate = round((self.metrics["cache_hits"] / total_cache_reqs * 100), 2) if total_cache_reqs > 0 else 0.0

            total_errs = sum(self.metrics["api_errors"].values())
            total_api_calls = sum(self.metrics["total_requests"].values())
            error_rate = round((total_errs / total_api_calls * 100), 2) if total_api_calls > 0 else 0.0

            return {
                "date": self._current_day,
                "daily_quota_used": self.metrics["daily_request_count"],
                "daily_quota_limit": self.quota_limit,
                "daily_quota_percent": round((self.metrics["daily_request_count"] / self.quota_limit) * 100, 2),
                "cache_hit_rate_percent": cache_hit_rate,
                "error_rate_percent": error_rate,
                "metrics": dict(self.metrics)
            }


# Singleton instance
goong_metrics = GoongMetricsCollector()
