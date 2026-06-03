from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from ..database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    instance_id = Column(Integer, ForeignKey("shift_instances.id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="Pending")
    # "Confirmed", "Cancelled", "Pending"
    amount_paid = Column(Float, nullable=True)   # cuánto pagó al reservar
    payment_status = Column(String, default="partial")
    # "partial" -> pagó el 50% de seña
    # "paid"    -> pagó el 100%

    instance = relationship("ShiftInstance", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    subscription = relationship("Subscription", back_populates="bookings")