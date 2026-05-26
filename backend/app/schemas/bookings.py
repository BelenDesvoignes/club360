from pydantic import BaseModel
from datetime import date as dt_date, datetime
from typing import Optional

class BookingCreate(BaseModel):
    instance_id: int

class BookingOut(BaseModel):
    id: int
    user_id: int
    instance_id: int
    status: str

    class Config:
        from_attributes = True


class BookingListOut(BaseModel):
    id: int
    user_id: int
    instance_id: int
    status: str
    subscription_id: Optional[int] = None
    is_subscription: bool = False
    amount_paid: Optional[float] = None
    payment_status: Optional[str] = None
    created_at: datetime
    activity_name: Optional[str] = None
    date: Optional[dt_date] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    price: Optional[float] = None

    class Config:
        from_attributes = True
