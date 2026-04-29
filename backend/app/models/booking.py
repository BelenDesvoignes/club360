from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    id_session = Column(Integer) # Conecta con Clase (Session)
    status = Column(String, default="pending") # confirmed, cancelled, pending
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")