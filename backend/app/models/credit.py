from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Credit(Base):
    __tablename__ = "credits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    amount = Column(Float, nullable=False) # Valor de la seña/clase
    activity_id = Column(Integer) # Debe usarse en la misma actividad
    created_at = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime) # Vence al mes siguiente
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="credits")