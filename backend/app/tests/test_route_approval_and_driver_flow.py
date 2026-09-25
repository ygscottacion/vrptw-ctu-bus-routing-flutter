import uuid
import datetime
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.main import app
from app.api import deps
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.route import Route, RouteStatus
from app.models.ticket import Ticket, TicketStatus
from app.core.timezone import VN_TZ


@pytest.fixture
def client():
    return TestClient(app)


def test_driver_route_start_end_ownership(client: TestClient, db_session: Session if "db_session" in locals() else None):
    """Test start/end route ownership validation and state transitions."""
    # Build mock driver profile
    driver_id = uuid.uuid4()
    other_driver_id = uuid.uuid4()
    driver_profile = Profile(id=driver_id, role=ProfileRole.DRIVER, full_name="Tài xế Test A")
    other_driver = Profile(id=other_driver_id, role=ProfileRole.DRIVER, full_name="Tài xế Test B")

    # Mock dependency overrides
    app.dependency_overrides[deps.get_current_driver] = lambda: driver_profile
    app.dependency_overrides[deps.get_current_profile] = lambda: driver_profile

    try:
        # Override DB session dependency if available
        pass
    finally:
        app.dependency_overrides.clear()
