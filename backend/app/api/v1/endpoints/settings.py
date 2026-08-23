from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_settings
from app.models.user import User
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter()


@router.get("/", response_model=SettingsResponse)
def get_settings(db: Session = Depends(deps.get_db)) -> Any:

    return crud_settings.get_settings(db)


@router.put("/ticket-price", response_model=SettingsResponse)
def update_ticket_price(
    settings_in: SettingsUpdate,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:

    return crud_settings.update_ticket_price(db=db, price=settings_in.ticket_price)
