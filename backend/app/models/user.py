import enum
from sqlalchemy import DateTime, Column, Integer, String, Boolean, Enum, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
from datetime import datetime


class UserRole(enum.Enum):
    CLIENT = "cliente"
    EMPLOYEE = "empleado"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    dni = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    profile_photo_url = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CLIENT)
    is_suspended = Column(Boolean, default=False)
    missed_classes_count = Column(Integer, default=0)


# RELATIONSHIPS
    cards = relationship("Card", back_populates="user")
    #asistencias
    attendances = relationship("Attendance", back_populates="user")
    suspensions = relationship("Suspension", back_populates="user")
    bookings = relationship("Booking", back_populates="user") # "Reserva" -> Booking
    payments = relationship("Payment", back_populates="user")
    credits = relationship("Credit", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    #susbscription es abono

    def __repr__(self):
        return f"<User {self.email} - Role: {self.role.value}>"
