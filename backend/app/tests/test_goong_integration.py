import pytest
from app.services.student_routing.helpers.distance_matrix import GoongDistanceMatrixProvider

SAMPLE_POINTS = [
    {"lat": 10.0302, "lng": 105.7721},  # CTU Campus
    {"lat": 10.0342, "lng": 105.7876},  # Ninh Kieu Quay
]

@pytest.mark.integration
def test_goong_distance_matrix_real_api_call():
    provider = GoongDistanceMatrixProvider(
        api_key="7WSy0ek8OLEv1HZvB9oikhHT6hVrohUdCLShbK8S"
    )
    dist_matrix, time_matrix, source = provider.get_matrix(SAMPLE_POINTS)

    assert source == "GOONG"
    assert len(dist_matrix) == 2
    assert len(time_matrix) == 2
    # Distance from CTU to Ninh Kieu Quay should be around 2-4 km
    assert 1.0 < dist_matrix[0][1] < 10.0
    # Travel time should be between 2 and 30 minutes
    assert 1.0 < time_matrix[0][1] < 30.0
    assert dist_matrix[0][0] == 0.0
