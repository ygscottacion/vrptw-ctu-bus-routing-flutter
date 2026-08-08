from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_route
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.schemas.route import RouteResponse, RouteGenerateRequest
from app.services.vrptw_solver import VRPTWSolverService

router = APIRouter()

@router.post("/generate", response_model=List[RouteResponse])
def generate_routes(
    request: RouteGenerateRequest,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Trigger VRPTW Solver Pipeline (Sweep + Tabu Search) to calculate and store optimized bus routes.
    """
    depot_loc = db.query(Location).filter(Location.id == request.depot_location_id).first()
    if not depot_loc:
        raise HTTPException(status_code=404, detail="Depot location not found")

    locations_db = db.query(Location).filter(Location.id != request.depot_location_id).all()
    vehicles_db = db.query(Vehicle).all()

    if not vehicles_db:
        raise HTTPException(status_code=400, detail="No vehicles available in system")

    depot_dict = {"id": depot_loc.id, "name": depot_loc.name, "latitude": depot_loc.latitude, "longitude": depot_loc.longitude}
    locations_dict = [
        {"id": loc.id, "name": loc.name, "latitude": loc.latitude, "longitude": loc.longitude, "demand": loc.demand}
        for loc in locations_db
    ]
    vehicles_dict = [
        {"id": v.id, "license_plate": v.license_plate, "capacity": v.capacity}
        for v in vehicles_db
    ]

    solver = VRPTWSolverService()
    results = solver.solve(depot_dict, locations_dict, vehicles_dict)

    created_routes = []
    for res in results:
        route_obj = crud_route.create_route(
            db=db,
            vehicle_id=res["vehicle_id"],
            route_date=request.date,
            total_distance=res["total_distance_km"],
            stops_data=res["ordered_stops"]
        )
        created_routes.append(route_obj)

    return created_routes

@router.get("/{route_id}", response_model=RouteResponse)
def get_route_details(
    route_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Get detailed route stops and coordinates for Flutter Map rendering.
    """
    route = crud_route.get_route_by_id(db, route_id=route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route

@router.get("/driver/{driver_id}", response_model=List[RouteResponse])
def get_driver_routes(
    driver_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Get assigned daily bus routes for a specific driver.
    """
    return crud_route.get_routes_by_driver(db, driver_id=driver_id)
