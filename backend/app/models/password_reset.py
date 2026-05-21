# api/backend/app/models/password_reset.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from ..database import Base  # ajustá el import según cómo tengas Base definido

class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)