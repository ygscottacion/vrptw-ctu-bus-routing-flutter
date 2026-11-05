import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.notification import Notification
from app.models.profile import Profile
from app.schemas.notification import NotificationReadRequest, NotificationResponse

router = APIRouter()


@router.get("/me", response_model=List[NotificationResponse])
def read_my_notifications(
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_profile.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )


@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_my_notification(
    notification_id: uuid.UUID,
    request: NotificationReadRequest,
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_profile.id)
        .one_or_none()
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông báo.")
    notification.is_read = request.is_read
    db.commit()
    db.refresh(notification)
    return notification
