from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class Subscription(Base): # Opcional: usar un Enum para estados
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    id_base_shift = Column(Integer) # Conecta con Turno_base
    month = Column(Integer, nullable=False)
    status = Column(String, default="active") # active, pending, expired

    user = relationship("User", back_populates="subscriptions")