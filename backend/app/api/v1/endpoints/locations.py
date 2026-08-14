from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_location
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse

router = APIRouter()

@router.get("/", response_model=List[LocationResponse])
def read_locations(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve all bus stops / locations.
    """
    locations = crud_location.get_locations(db, skip=skip, limit=limit)
    return locations

@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    location_in: LocationCreate,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Create a new bus stop / location with time window and demand parameters.
    """
    return crud_location.create_location(db=db, location_in=location_in)

@router.get("/{location_id}", response_model=LocationResponse)
def read_location(
    location_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Get location details by ID.
    """
    location = crud_location.get_location(db=db, location_id=location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: int,
    location_in: LocationUpdate,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Update location information.
    """
    location = crud_location.get_location(db=db, location_id=location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return crud_location.update_location(db=db, db_obj=location, location_in=location_in)

@router.delete("/{location_id}", response_model=LocationResponse)
def delete_location(
    location_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Delete a location by ID.
    """
    location = crud_location.get_location(db=db, location_id=location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return crud_location.delete_location(db=db, location_id=location_id)
