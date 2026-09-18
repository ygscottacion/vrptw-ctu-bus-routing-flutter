import json
import pytest
from unittest.mock import patch, MagicMock
import urllib.error

from app.services.student_routing.helpers.distance_matrix import (
    GoongDistanceMatrixProvider,
    StaticDistanceMatrixProvider,
    OSRMWithFallbackProvider
)

SAMPLE_POINTS = [
    {"lat": 10.0302, "lng": 105.7721},  # CTU Campus
    {"lat": 10.0342, "lng": 105.7876},  # Ninh Kieu Quay
    {"lat": 10.0031, "lng": 105.7482}   # Cai Rang Market
]

GOONG_SUCCESS_RESPONSE = {
    "rows": [
        {
            "elements": [
                {"distance": {"value": 0}, "duration": {"value": 0}, "status": "OK"},
                {"distance": {"value": 2500}, "duration": {"value": 300}, "status": "OK"},
                {"distance": {"value": 5000}, "duration": {"value": 600}, "status": "OK"}
            ]
        },
        {
            "elements": [
                {"distance": {"value": 2500}, "duration": {"value": 300}, "status": "OK"},
                {"distance": {"value": 0}, "duration": {"value": 0}, "status": "OK"},
                {"distance": {"value": 4000}, "duration": {"value": 500}, "status": "OK"}
            ]
        },
        {
            "elements": [
                {"distance": {"value": 5000}, "duration": {"value": 600}, "status": "OK"},
                {"distance": {"value": 4000}, "duration": {"value": 500}, "status": "OK"},
                {"distance": {"value": 0}, "duration": {"value": 0}, "status": "OK"}
            ]
        }
    ]
}


def test_goong_distance_matrix_happy_path():
    provider = GoongDistanceMatrixProvider(api_key="7WSy0ek8OLEv1HZvB9oikhHT6hVrohUdCLShbK8S")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(GOONG_SUCCESS_RESPONSE).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        dist_matrix, time_matrix, source = provider.get_matrix(SAMPLE_POINTS)

    assert source == "GOONG"
    assert len(dist_matrix) == 3
    assert len(time_matrix) == 3

    # 2500m -> 2.5km, 300s -> 5.0 min
    assert dist_matrix[0][1] == 2.5
    assert time_matrix[0][1] == 5.0
    assert dist_matrix[0][0] == 0.0
    assert time_matrix[0][0] == 0.0


def test_goong_distance_matrix_missing_key_fallback(caplog):
    provider = GoongDistanceMatrixProvider(api_key="")
    dist_matrix, time_matrix, source = provider.get_matrix(SAMPLE_POINTS)

    assert source == "STATIC_FALLBACK"
    assert len(dist_matrix) == 3
    assert "Missing or unconfigured GOONG_API_KEY" in caplog.text


def test_goong_distance_matrix_auth_error_fallback(caplog):
    provider = GoongDistanceMatrixProvider(api_key="INVALID_KEY")

    mock_err = urllib.error.HTTPError(
        url="https://rsapi.goong.io/DistanceMatrix",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=None
    )

    with patch("urllib.request.urlopen", side_effect=mock_err):
        dist_matrix, time_matrix, source = provider.get_matrix(SAMPLE_POINTS)

    assert source == "STATIC_FALLBACK"
    assert len(dist_matrix) == 3
    assert "401" in caplog.text
    assert "ALERT [FALLBACK_TRIGGERED]" in caplog.text


def test_goong_distance_matrix_rate_limit_fallback(caplog):
    provider = GoongDistanceMatrixProvider(api_key="7WSy0ek8OLEv1HZvB9oikhHT6hVrohUdCLShbK8S")

    mock_err = urllib.error.HTTPError(
        url="https://rsapi.goong.io/DistanceMatrix",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=None
    )

    with patch("urllib.request.urlopen", side_effect=mock_err):
        dist_matrix, time_matrix, source = provider.get_matrix(SAMPLE_POINTS)

    assert source == "STATIC_FALLBACK"
    assert "429" in caplog.text
    assert "ALERT [FALLBACK_TRIGGERED]" in caplog.text


def test_goong_distance_matrix_timeout_fallback(caplog):
    provider = GoongDistanceMatrixProvider(api_key="7WSy0ek8OLEv1HZvB9oikhHT6hVrohUdCLShbK8S", timeout=0.01)

    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        dist_matrix, time_matrix, source = provider.get_matrix(SAMPLE_POINTS)

    assert source == "STATIC_FALLBACK"
    assert "Request timed out" in caplog.text
    assert "ALERT [FALLBACK_TRIGGERED]" in caplog.text


def test_osrm_deprecated_warning():
    with pytest.deprecated_call():
        provider = OSRMWithFallbackProvider()
        assert provider.timeout == 3.0
