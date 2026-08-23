from sqlalchemy.orm import Session
from app.models.settings import SystemSetting


def get_settings(db: Session) -> SystemSetting:
    settings = db.query(SystemSetting).first()
    if not settings:
        settings = SystemSetting(ticket_price=0)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_ticket_price(db: Session, price: float) -> SystemSetting:
    settings = get_settings(db)
    settings.ticket_price = price
    db.commit()
    db.refresh(settings)
    return settings
