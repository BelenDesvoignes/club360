from datetime import datetime

from pydantic import BaseModel, Field

from ..models.card import CardStatus


class CardUpsert(BaseModel):
    card_holder: str = Field(..., min_length=2, max_length=120)
    last_four: str = Field(..., min_length=4, max_length=4)
    expiry_date: str = Field(..., min_length=5, max_length=5, description="MM/AA")
    brand: str | None = Field(default=None, max_length=50)
    status: CardStatus = CardStatus.ACTIVE


class CardOut(BaseModel):
    id: int
    user_id: int
    card_holder: str
    last_four: str
    expiry_date: str
    brand: str | None = None
    status: CardStatus
    created_at: datetime

    class Config:
        from_attributes = True
