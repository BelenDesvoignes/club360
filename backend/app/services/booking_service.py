from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from ..models.booking import Booking
from ..models.user import User
from ..models.shift_instance import ShiftInstance
from ..models.subscription import Subscription
from ..models.suspension import Suspension
from ..models.payment import Payment
from fastapi import HTTPException, status


def is_user_suspended(db: Session, user_id: int) -> bool:
    """Check if user has an active suspension."""
    suspension = (
        db.query(Suspension)
        .filter(
            and_(
                Suspension.user_id == user_id,
                Suspension.status == "active",
                Suspension.end_date == None  # No end date means still active
            )
        )
        .first()
    )
    return suspension is not None


def is_user_abonado(db: Session, user_id: int, template_id: int) -> bool:
    """Check if user has an active subscription for this template."""
    subscription = (
        db.query(Subscription)
        .filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.template_id == template_id,
                Subscription.status == "active"
            )
        )
        .first()
    )
    return subscription is not None


def has_instance_capacity(db: Session, instance_id: int) -> bool:
    """Check if instance has available capacity."""
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instancia no encontrada")
    
    template = instance.template
    if not template:
        raise HTTPException(status_code=500, detail="Template no encontrado para la instancia")
    
    # Count current bookings (excluding cancelled)
    booked_count = (
        db.query(Booking)
        .filter(
            and_(
                Booking.instance_id == instance_id,
                Booking.status != "Cancelled"
            )
        )
        .count()
    )
    
    return booked_count < template.capacity


def get_instance_booked_count(db: Session, instance_id: int) -> int:
    """Get number of confirmed bookings for instance."""
    return (
        db.query(Booking)
        .filter(
            and_(
                Booking.instance_id == instance_id,
                Booking.status != "Cancelled"
            )
        )
        .count()
    )


def create_booking(db: Session, user_id: int, instance_id: int) -> Booking:
    """
    Create a booking with complete business logic validation.
    
    Business Rules:
    1. User cannot be suspended
    2. Instance must have available capacity
    3. If user is not abonado, they must pay 50% or 100% seña
    4. If user is abonado for that activity, booking is auto-confirmed
    5. Cannot book past class dates
    
    Returns: Booking object with status "Confirmed" or "Pending"
    Raises: HTTPException with appropriate error
    """
    
    # Get user
    user = db.query(User).filter(User.id_user == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Get instance
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    
    template = instance.template
    if not template:
        raise HTTPException(status_code=500, detail="Template no encontrado")
    
    # Rule 1: Check if user is suspended
    if is_user_suspended(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está suspendida. Debes solicitar reactivación para hacer nuevas reservas."
        )
    
    # Rule 5: Check if booking date is in the future
    if instance.date < datetime.now().date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes hacer reservas para clases pasadas"
        )
    
    # Check if user already has a booking for this instance
    existing_booking = (
        db.query(Booking)
        .filter(
            and_(
                Booking.user_id == user_id,
                Booking.instance_id == instance_id,
                Booking.status != "Cancelled"
            )
        )
        .first()
    )
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tienes una reserva para este turno"
        )
    
    # Rule 2: Check capacity
    if not has_instance_capacity(db, instance_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay cupos disponibles para este turno. Únetea la lista de espera."
        )
    
    # Rule 3 & 4: Check if user is abonado for this activity
    is_abonado = is_user_abonado(db, user_id, template.id)
    
    # Create booking
    booking = Booking(
        user_id=user_id,
        instance_id=instance_id,
        status="Confirmed" if is_abonado else "Pending"
    )
    
    db.add(booking)
    
    # For non-abonado users, create a Pending payment of 50% (seña)
    if not is_abonado:
        seña_amount = template.price * 0.5  # 50% deposit
        payment = Payment(
            user_id=user_id,
            amount=seña_amount,
            status="pending",
            type="booking"
        )
        db.add(payment)
    
    db.commit()
    db.refresh(booking)
    
    return booking


def cancel_booking(db: Session, booking_id: int, user_id: int) -> Booking:
    """
    Cancel a booking. Only owner or admin can cancel.
    Returns the cancelled booking.
    """
    from ..models.user import UserRole
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # Check authorization
    user = db.query(User).filter(User.id_user == user_id).first()
    if booking.user_id != user_id and (not user or user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para cancelar esta reserva"
        )
    
    booking.status = "Cancelled"
    db.commit()
    db.refresh(booking)
    
    return booking
