import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


def get_vehicles(db: Session, skip: int = 0, limit: int = 100) -> List[Vehicle]:
    return db.query(Vehicle).offset(skip).limit(limit).all()


def get_vehicle(db: Session, vehicle_id: uuid.UUID) -> Optional[Vehicle]:
    return db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()


def create_vehicle(db: Session, vehicle_in: VehicleCreate) -> Vehicle:
    db_obj = Vehicle(
        id=uuid.uuid4(),
        license_plate=vehicle_in.license_plate,
        capacity=vehicle_in.capacity,
        driver_id=vehicle_in.driver_id,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_vehicle(db: Session, db_obj: Vehicle, vehicle_in: VehicleUpdate) -> Vehicle:
    update_data = vehicle_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def assign_driver(db: Session, vehicle_id: uuid.UUID, driver_id: Optional[uuid.UUID]) -> Optional[Vehicle]:
    vehicle = get_vehicle(db, vehicle_id)
    if vehicle:
        vehicle.driver_id = driver_id
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle_id: uuid.UUID) -> Optional[Vehicle]:
    db_obj = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if db_obj:
        db.delete(db_obj)
        db.commit()
    return db_obj
