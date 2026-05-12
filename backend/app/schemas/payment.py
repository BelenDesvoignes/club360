from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PaymentResponse(BaseModel):
    id: int
    amount: float
    status: Optional[str] = None
    type: Optional[str] = None
    date: datetime

    class Config:
        from_attributes = True