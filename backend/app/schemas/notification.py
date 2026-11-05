import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationReadRequest(BaseModel):
    is_read: bool = True
