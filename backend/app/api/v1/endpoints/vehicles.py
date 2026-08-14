from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_vehicle
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse

router = APIRouter()

@router.get("/", response_model=List[VehicleResponse])
def read_vehicles(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve all bus vehicles.
    """
    return crud_vehicle.get_vehicles(db, skip=skip, limit=limit)

@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    vehicle_in: VehicleCreate,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Create a new bus vehicle.
    """
    return crud_vehicle.create_vehicle(db=db, vehicle_in=vehicle_in)

@router.get("/{vehicle_id}", response_model=VehicleResponse)
def read_vehicle(
    vehicle_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Get vehicle details by ID.
    """
    vehicle = crud_vehicle.get_vehicle(db=db, vehicle_id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: int,
    vehicle_in: VehicleUpdate,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Update vehicle specifications or assigned driver.
    """
    vehicle = crud_vehicle.get_vehicle(db=db, vehicle_id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return crud_vehicle.update_vehicle(db=db, db_obj=vehicle, vehicle_in=vehicle_in)

@router.put("/{vehicle_id}/driver", response_model=VehicleResponse)
def assign_vehicle_driver(
    vehicle_id: int,
    driver_id: Optional[int] = None,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Assign or unassign a driver for a specific vehicle.
    """
    vehicle = crud_vehicle.assign_driver(db=db, vehicle_id=vehicle_id, driver_id=driver_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.delete("/{vehicle_id}", response_model=VehicleResponse)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Delete a vehicle by ID.
    """
    vehicle = crud_vehicle.get_vehicle(db=db, vehicle_id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return crud_vehicle.delete_vehicle(db=db, vehicle_id=vehicle_id)
