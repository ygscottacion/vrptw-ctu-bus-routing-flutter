import json
import pytest
from app.services.student_routing.helpers.goong_metrics import GoongMetricsCollector

def test_metrics_collector_logging_and_summary(caplog):
    collector = GoongMetricsCollector(quota_limit=10)

    # 1. Log Direction call (Cache Miss)
    log1 = collector.log_goong_call("direction", "10.03,105.77->10.04,105.78", latency_ms=120.5, status_code=200, cache_hit=False)
    assert log1["endpoint"] == "direction"
    assert log1["cache_hit"] is False
    assert log1["daily_quota_used"] == 1
    assert log1["daily_quota_percent"] == 10.0

    # 2. Log Direction call (Cache Hit)
    log2 = collector.log_goong_call("direction", "10.03,105.77->10.04,105.78", latency_ms=0.0, status_code=200, cache_hit=True)
    assert log2["cache_hit"] is True
    assert log2["daily_quota_used"] == 2

    # 3. Log Distance Matrix error
    log3 = collector.log_goong_call("distance_matrix", "points_count=3", latency_ms=45.0, status_code=429, error="Rate limit exceeded")
    assert log3["status_code"] == 429

    summary = collector.get_metrics_summary()
    assert summary["daily_quota_used"] == 3
    assert summary["cache_hit_rate_percent"] == 33.33
    assert summary["metrics"]["api_errors"]["429"] == 1


def test_eta_anomaly_detection(caplog):
    collector = GoongMetricsCollector()

    # Normal speed (10km in 15 mins -> 40 km/h) -> No anomaly
    res_normal = collector.validate_eta_anomaly(distance_km=10.0, duration_minutes=15.0, origin_dest_summary="test_route")
    assert res_normal is None

    # Unrealistic high speed (100km in 10 mins -> 600 km/h) -> Trigger anomaly
    res_fast = collector.validate_eta_anomaly(distance_km=100.0, duration_minutes=10.0, origin_dest_summary="fast_route")
    assert res_fast is not None
    assert "ALERT [ETA_ANOMALY]" in caplog.text
    assert "Unrealistic high speed" in caplog.text

    # Unrealistic slow speed (10km in 360 mins -> 1.67 km/h) -> Trigger anomaly
    res_slow = collector.validate_eta_anomaly(distance_km=10.0, duration_minutes=360.0, origin_dest_summary="slow_route")
    assert res_slow is not None
    assert "Unrealistic slow speed" in caplog.text

    # Negative / 0 duration -> Trigger anomaly
    res_zero = collector.validate_eta_anomaly(distance_km=5.0, duration_minutes=0.0, origin_dest_summary="zero_dur")
    assert res_zero is not None
    assert "Invalid duration" in caplog.text


def test_quota_alert_warning(caplog):
    collector = GoongMetricsCollector(quota_limit=10)

    # Make 8 requests (80% quota)
    for _ in range(8):
        collector.log_goong_call("direction", "test", 10.0, 200)

    assert "ALERT [QUOTA_NEAR_LIMIT]" in caplog.text
    assert "quota reached 80.0%" in caplog.text
