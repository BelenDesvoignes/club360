from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    id_session = Column(Integer) # Conecta con la clase específica
    is_present = Column(Boolean, default=False)

    user = relationship("User", back_populates="attendances")