from datetime import datetime

from pydantic import BaseModel


class PaymentCompleteBookingRequest(BaseModel):
    amount: float
    booking_id: int | None = None


class PaymentResponse(BaseModel):
    id: int
    amount: float
    status: str | None = None
    type: str | None = None
    activity_id: int | None = None
    date: datetime
    # 🌟 AGREGAMOS ESTO: Permitimos que el deporte viaje en el JSON hacia la web
    sport_name: str | None = None

    class Config:
        from_attributes = True
