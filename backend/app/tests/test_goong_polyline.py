import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.services.student_routing.helpers.goong_direction import GoongDirectionService, decode_polyline
from app.api.v1.endpoints.routes import get_route_polyline, _check_rate_limit

GOONG_DIRECTION_RESPONSE = {
    "routes": [
        {
            "overview_polyline": {
                "points": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
            },
            "legs": [
                {
                    "distance": {"text": "2.5 km", "value": 2500},
                    "duration": {"text": "5 mins", "value": 300}
                }
            ]
        }
    ],
    "status": "OK"
}


def test_decode_polyline():
    # Standard polyline string decode test
    pts = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert len(pts) > 0
    assert len(pts[0]) == 2


def test_goong_direction_service_cache_hit_and_miss():
    service = GoongDirectionService(ttl_seconds=3600)
    waypoints = [(10.0302, 105.7721), (10.0342, 105.7876)]

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(GOONG_DIRECTION_RESPONSE).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        # 1st call -> Cache Miss
        res1 = service.get_route_polyline(waypoints)
        assert res1["cached"] is False
        assert res1["distance_km"] == 2.5
        assert res1["duration_minutes"] == 5.0
        assert len(res1["points"]) > 0

        # 2nd call with same waypoints -> Cache Hit
        res2 = service.get_route_polyline(waypoints)
        assert res2["cached"] is True
        assert res2["distance_km"] == 2.5


def test_polyline_endpoint_handler_validation():
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"

    # Missing parameters raises 400
    with pytest.raises(HTTPException) as exc1:
        get_route_polyline(request=mock_request, origin=None, destination=None, waypoints=None, current_profile=MagicMock())
    assert exc1.value.status_code == 400

    # Invalid waypoints format raises 400
    with pytest.raises(HTTPException) as exc2:
        get_route_polyline(request=mock_request, origin=None, destination=None, waypoints="invalid_coords", current_profile=MagicMock())
    assert exc2.value.status_code == 400


def test_polyline_endpoint_rate_limiting():
    # Test rate limit function (max 2 req for test)
    ip = "192.168.1.99"
    _check_rate_limit(ip, limit=2, window_seconds=60.0)
    _check_rate_limit(ip, limit=2, window_seconds=60.0)

    with pytest.raises(HTTPException) as exc:
        _check_rate_limit(ip, limit=2, window_seconds=60.0)
    assert exc.value.status_code == 429

