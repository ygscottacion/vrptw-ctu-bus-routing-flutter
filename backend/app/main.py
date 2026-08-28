from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import Base, engine  # <--- DÒNG NÀY ĐANG BỊ THIẾU

from app.models import incident, location, route, ticket, user, vehicle, booking

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Tự động tạo tất cả các bảng chưa có trong DB
#Base.metadata.create_all(bind=engine)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for mobile / web admin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db

@app.get("/")
def root():
    return {
        "message": "Welcome to CTU Bus Routing API System (VRPTW)",
        "docs": "/docs"
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "provider": "Supabase Cloud"}
    except Exception as e:
        return {"status": "error", "database": str(e)}

@app.get("/ready")
def readiness_check():
    return {"status": "ready"}
