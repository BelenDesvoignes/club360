from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    amount = Column(Float, nullable=False)
    status = Column(String) # pending, partial, completed
    type = Column(String) # subscription or booking
    date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")