import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate


def get_locations(db: Session, skip: int = 0, limit: int = 100) -> List[Location]:
    return db.query(Location).offset(skip).limit(limit).all()


def get_location(db: Session, location_id: uuid.UUID) -> Optional[Location]:
    return db.query(Location).filter(Location.id == location_id).first()


def create_location(db: Session, location_in: LocationCreate) -> Location:
    db_obj = Location(
        id=uuid.uuid4(),
        name=location_in.name,
        latitude=location_in.latitude,
        longitude=location_in.longitude,
        time_window_start=location_in.time_window_start,
        time_window_end=location_in.time_window_end,
        demand=location_in.demand,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_location(db: Session, db_obj: Location, location_in: LocationUpdate) -> Location:
    update_data = location_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_location(db: Session, location_id: uuid.UUID) -> Optional[Location]:
    db_obj = db.query(Location).filter(Location.id == location_id).first()
    if db_obj:
        db.delete(db_obj)
        db.commit()
    return db_obj
