#abono

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    # CORRECCIÓN: Apuntar al template
    template_id = Column(Integer, ForeignKey("shift_templates.id"))
    month = Column(Integer, nullable=False)
    status = Column(String, default="active")

    user = relationship("User", back_populates="subscriptions")
    template = relationship("ShiftTemplate", back_populates="subscriptions")