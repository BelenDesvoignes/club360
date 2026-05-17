from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, func
from sqlalchemy.orm import relationship
from app.database import Base

# 1. ACTIVIDAD (Fútbol, Vóley...)
class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    court = Column(String) #cancha
    is_active = Column(Boolean, default=True, server_default='true', nullable=False) #para borrado logico

    templates = relationship("ShiftTemplate", back_populates="activity")


