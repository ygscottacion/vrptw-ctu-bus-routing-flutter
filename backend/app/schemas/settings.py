from pydantic import BaseModel, ConfigDict


class SettingsResponse(BaseModel):
    ticket_price: float

    model_config = ConfigDict(from_attributes=True)


class SettingsUpdate(BaseModel):
    ticket_price: float
