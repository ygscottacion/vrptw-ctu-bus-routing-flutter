from fastapi import APIRouter
from app.api.v1.endpoints import auth, routes

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(routes.router, prefix="/routes", tags=["Routing & VRPTW Algorithm"])
