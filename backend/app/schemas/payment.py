from datetime import datetime

from pydantic import BaseModel


class PaymentCompleteBookingRequest(BaseModel):
    amount: float
    booking_id: int | None = None


class SuspensionPaymentRequest(BaseModel):
    suspension_id: int
    amount: float | None = None


class SuspensionResponse(BaseModel):
    id: int
    reason: str
    status: str | None = None
    start_date: datetime
    end_date: datetime | None = None
    activity_id: int | None = None
    sport_name: str | None = None
    amount: float = 0
    payment_id: int | None = None

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    id: int
    amount: float
    status: str | None = None
    type: str | None = None
    date: datetime
    # Permitimos que el deporte viaje en el JSON hacia la web.
    sport_name: str | None = None
    activity_id: int | None = None

    class Config:
        from_attributes = True
