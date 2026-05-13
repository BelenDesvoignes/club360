#los turnos con fecha

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, func
from sqlalchemy.orm import relationship
from app.database import Base

# . SESIÓN / TURNO REAL (Martes 9 de Mayo)
class ShiftInstance(Base):
    __tablename__ = "shift_instances"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("shift_templates.id"))
    date = Column(Date)
    is_cancelled = Column(Boolean, default=False)
    # NUEVO: Capacidad específica para esta fecha
    capacity = Column(Integer, nullable=False) 

    template = relationship("ShiftTemplate", back_populates="instances")
    bookings = relationship("Booking", back_populates="instance")