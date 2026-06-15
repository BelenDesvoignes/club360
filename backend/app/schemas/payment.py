from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PaymentCompleteBookingRequest(BaseModel):
    amount: float
    booking_id: Optional[int] = None

class PaymentResponse(BaseModel):
    id: int
    amount: float
    status: Optional[str] = None
    type: Optional[str] = None
    date: datetime
    # 🌟 AGREGAMOS ESTO: Permitimos que el deporte viaje en el JSON hacia la web
    sport_name: Optional[str] = None 

    class Config:
        from_attributes = True