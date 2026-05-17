from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base

class WaitingList(Base):
    __tablename__ = "waiting_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_user"))
    instance_id = Column(Integer, ForeignKey("shift_instances.id"))

    # Posición en la cola (1, 2, 3...)
    position = Column(Integer, nullable=False)

    # Status: 'waiting', 'notified', 'converted' (si pasó a ser reserva), 'cancelled'
    status = Column(String, default="waiting")

    created_at = Column(DateTime, default=func.now())

    # Relaciones
    user = relationship("User")
    instance = relationship("ShiftInstance")

    def __repr__(self):
        return f"<WaitingList User:{self.user_id} Inst:{self.instance_id} Pos:{self.position}>"