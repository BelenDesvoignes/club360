from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String)  # pending, partial, completed
    type = Column(String)  # subscription or booking
    date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")


class PaymentResponse(BaseModel):
    id: int
    amount: float
    status: str | None = None
    type: str | None = None
    date: datetime

    class Config:
        from_attributes = True
