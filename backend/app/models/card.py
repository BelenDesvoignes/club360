import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class CardStatus(enum.Enum):
    ACTIVE = "Activa"
    EMPTY_FUNDS = "Sin Fondos"
    BLOCKED = "Bloqueada"


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user", ondelete="CASCADE"), nullable=False)
    card_holder = Column(String, nullable=False)
    last_four = Column(String(4), nullable=False)
    expiry_date = Column(String(5), nullable=False)
    brand = Column(String)
    status = Column(Enum(CardStatus, name="estado_tarjeta"), default=CardStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="cards")

    def __repr__(self):
        return f"<Card {self.brand} ****{self.last_four} - Status: {self.status.value}>"