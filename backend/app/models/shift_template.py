#turno base

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, func
from sqlalchemy.orm import relationship
from app.database import Base

class ShiftTemplate(Base):
    __tablename__ = "shift_templates"
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"))
    day_of_week = Column(String) # "Martes"
    start_time = Column(String)  # "17:00"
    capacity = Column(Integer)
    price = Column(Float, default=100.0)  # Precio de la clase en $

    activity = relationship("Activity", back_populates="templates")
    instances = relationship("ShiftInstance", back_populates="template")
    subscriptions = relationship("Subscription", back_populates="template")