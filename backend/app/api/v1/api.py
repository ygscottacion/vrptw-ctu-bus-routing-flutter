from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, locations, vehicles, routes, tickets, incidents, reports, websocket, bookings, reviews

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["User Management"])
api_router.include_router(locations.router, prefix="/locations", tags=["Bus Stops & Locations"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles Management"])
api_router.include_router(routes.router, prefix="/routes", tags=["Routing & VRPTW Algorithm"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets & Student Check-in"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["Driver Emergency Incidents"])
api_router.include_router(reports.router, prefix="/reports", tags=["Admin Dashboard Analytics"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["Pre-booking Routes"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Trip Reviews & Feedback"])
api_router.include_router(websocket.router, tags=["Realtime WebSocket Broadcast"])
