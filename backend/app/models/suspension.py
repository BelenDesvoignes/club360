from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base
from datetime import datetime

class Suspension(Base):
    __tablename__ = "suspensions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    reason = Column(String, nullable=False)  # "suspension_clase_libre" | "suspension_abono"
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active, lifted

    user = relationship("User", back_populates="suspensions")
    activity = relationship("Activity")