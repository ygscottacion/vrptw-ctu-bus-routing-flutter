import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.notification import Notification


def add_notification(
    db: Session, *, user_id: uuid.UUID, event_key: str, type: str, title: str, body: str
) -> None:
    """Add an idempotent notification in the caller's transaction."""
    values = dict(user_id=user_id, event_key=event_key, type=type, title=title, body=body)
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(
            insert(Notification).values(**values).on_conflict_do_nothing(
                constraint="uq_notifications_user_event"
            )
        )
        return
    if not db.query(Notification.id).filter_by(user_id=user_id, event_key=event_key).first():
        db.add(Notification(**values))
