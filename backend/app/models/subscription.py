from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Float
from sqlalchemy.orm import relationship

from ..database import Base
from datetime import datetime

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    # CORRECCIÓN: Apuntar al template
    template_id = Column(Integer, ForeignKey("shift_templates.id"))
    month = Column(Integer, nullable=False)
    status = Column(String, default="active")

    price_paid = Column(Float, nullable=True)
    purchase_date = Column(DateTime, nullable=True)
    valid_to = Column(Date, nullable=True)

    user = relationship("User", back_populates="subscriptions")
    template = relationship("ShiftTemplate", back_populates="subscriptions")
    bookings = relationship("Booking", back_populates="subscription")