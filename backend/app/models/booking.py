from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base
from datetime import datetime

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    instance_id = Column(Integer, ForeignKey("shift_instances.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    status = Column(String, default="Pending")
 # "Confirmed", "Cancelled", "Pending"

    instance = relationship("ShiftInstance", back_populates="bookings")
    user = relationship("User", back_populates="bookings")