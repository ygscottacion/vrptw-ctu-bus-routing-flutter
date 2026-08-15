import pytest
from app.crud import crud_location, crud_vehicle, crud_user
from app.schemas.location import LocationCreate, LocationUpdate
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.schemas.user import UserCreate
from app.models.user import UserRole
from app.core.database import Base, engine, SessionLocal

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_crud_user(db):
    username = "test_user_unique"
    existing = crud_user.get_user_by_username(db, username=username)
    if not existing:
        user_in = UserCreate(username=username, password="password123", role=UserRole.PASSENGER)
        user = crud_user.create_user(db, user_in=user_in)
        assert user.username == username
        assert user.id is not None

def test_crud_location(db):
    loc_in = LocationCreate(
        name="Trạm Test - ĐH Cần Thơ",
        latitude=10.0299,
        longitude=105.7684,
        demand=5
    )
    created = crud_location.create_location(db, location_in=loc_in)
    assert created.id is not None
    assert created.name == "Trạm Test - ĐH Cần Thơ"

    # Read
    fetched = crud_location.get_location(db, location_id=created.id)
    assert fetched is not None

    # Update
    update_in = LocationUpdate(demand=15)
    updated = crud_location.update_location(db, db_obj=fetched, location_in=update_in)
    assert updated.demand == 15

    # Delete
    deleted = crud_location.delete_location(db, location_id=created.id)
    assert deleted is not None

def test_crud_vehicle(db):
    veh_in = VehicleCreate(
        license_plate="65B-999.99",
        capacity=35
    )
    created = crud_vehicle.create_vehicle(db, vehicle_in=veh_in)
    assert created.id is not None
    assert created.license_plate == "65B-999.99"

    # Update driver
    assigned = crud_vehicle.assign_driver(db, vehicle_id=created.id, driver_id=1)
    assert assigned.driver_id == 1

    # Delete
    deleted = crud_vehicle.delete_vehicle(db, vehicle_id=created.id)
    assert deleted is not None
