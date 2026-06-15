from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date, timedelta
import calendar
from ..models.booking import Booking
from ..models.user import User
from ..models.shift_instance import ShiftInstance
from ..models.subscription import Subscription
from ..models.suspension import Suspension
from ..models.payment import Payment
from ..models.credit import Credit  # Importamos el modelo de créditos necesario
from .subscription_service import ensure_user_suspension_if_unpaid
from fastapi import HTTPException, status
from ..time_override import business_today, business_utcnow


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


def _subscription_covers_date(subscription: Subscription, target_date: date) -> bool:
    """Return True if this subscription should count as active for a given class date.

    Backwards compatibility: legacy subscriptions can have NULL purchase_date/valid_to.
    """
    if not target_date:
        return False

    purchase_date = subscription.purchase_date.date() if subscription.purchase_date else None
    valid_to = subscription.valid_to

    if purchase_date and target_date < purchase_date:
        return False
    if valid_to and target_date > valid_to:
        return False
    return True


def get_active_subscription(db: Session, user_id: int, template_id: int, *, for_date: date | None = None) -> Subscription | None:
    """Return an active subscription for this template (optionally covering a given date)."""
    subscriptions = (
        db.query(Subscription)
        .filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.template_id == template_id,
                Subscription.status == "active",
            )
        )
        .order_by(Subscription.purchase_date.desc().nullslast(), Subscription.id.desc())
        .all()
    )

    if not subscriptions:
        return None
    if not for_date:
        return subscriptions[0]

    for subscription in subscriptions:
        if _subscription_covers_date(subscription, for_date):
            return subscription
    return None


def is_user_abonado(db: Session, user_id: int, template_id: int, *, for_date: date | None = None) -> bool:
    return get_active_subscription(db, user_id, template_id, for_date=for_date) is not None


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


def create_booking(db: Session, user_id: int, instance_id: int | None, subscription_id: int | None = None) -> Booking:
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
    if not instance_id:
        raise HTTPException(status_code=400, detail="Falta el identificador del turno para procesar la reserva.")

    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    
    template = instance.template
    if not template:
        raise HTTPException(status_code=500, detail="Template no encontrado")
    
    # Lazy rule: after day 10, auto-suspend if unpaid (TP-friendly; no cron required)
    ensure_user_suspension_if_unpaid(db, user_id=user_id)

    # Rule 1: Check if user is suspended
    if is_user_suspended(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está suspendida. Debes solicitar reactivación para hacer nuevas reservas."
        )
    
    # Rule 5: Check if booking date is in the future
    if instance.date < business_today():
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
            detail="No hay cupos disponibles para este turno. Únete a la lista de espera."
        )
    
    # Rule 3 & 4: Check if user is abonado for this template (or if a subscription_id was explicitly passed)
    active_subscription = None
    if subscription_id:
        active_subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    if not active_subscription:
        active_subscription = get_active_subscription(db, user_id, template.id, for_date=instance.date)
        
    is_abonado = active_subscription is not None
    
    # Create booking
    booking = Booking(
        user_id=user_id,
        instance_id=instance_id,
        created_at=business_utcnow(),
        status="Confirmed" if is_abonado else "Pending",
        subscription_id=active_subscription.id if active_subscription else None,
        amount_paid=0,
        payment_status="paid" if is_abonado else "partial",
    )
    
    db.add(booking)
    
    # For non-abonado users, create a Pending payment of 50% (seña)
    if not is_abonado:
        seña_amount = template.price * 0.5  # 50% deposit
        payment = Payment(
            user_id=user_id,
            amount=seña_amount,
            status="pending",
            type="booking",
            date=business_utcnow(),
        )
        db.add(payment)
    
    db.commit()
    db.refresh(booking)
    
    return booking


def cancel_booking(db: Session, booking_id: int, user_id: int) -> Booking:
    """
    Cancel a booking. Only owner or admin can cancel.
    Checks time limit (48hs) and payment status to award a credit if valid.
    Uses business time overrides for demo simulation compatibility.
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
        
    if booking.status == "Cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta reserva ya se encuentra cancelada"
        )

    instance = db.query(ShiftInstance).filter(ShiftInstance.id == booking.instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instancia de turno no encontrada")

    class_datetime = business_utcnow()
    if instance.date and instance.template and instance.template.start_time:
        try:
            time_parts = list(map(int, instance.template.start_time.split(":")))
            class_datetime = datetime.combine(
                instance.date, 
                datetime.min.time().replace(hour=time_parts[0], minute=time_parts[1])
            )
        except Exception:
            class_datetime = datetime.combine(instance.date, datetime.min.time())

    time_difference = class_datetime - business_utcnow()
    is_in_time = time_difference >= timedelta(hours=48)

    is_fully_paid = booking.payment_status == "paid" or booking.subscription_id is not None

    if is_in_time and is_fully_paid:
        activity_id = instance.template.activity_id if instance.template else 1

      
        ahora_simulado = business_utcnow()
        next_month = ahora_simulado.month + 1 if ahora_simulado.month < 12 else 1
        next_month_year = ahora_simulado.year if ahora_simulado.month < 12 else ahora_simulado.year + 1
        last_day_next_month = calendar.monthrange(next_month_year, next_month)[1]
        expiry_date_str = f"{next_month_year}-{str(next_month).zfill(2)}-{str(last_day_next_month).zfill(2)}"

        existing_credit = db.query(Credit).filter(
            and_(
                Credit.user_id == booking.user_id,
                Credit.activity_id == activity_id,
                Credit.is_used == False
            )
        ).first()

        if existing_credit:
            existing_credit.amount += 1.0
        else:
            new_credit = Credit(
                user_id=booking.user_id,
                amount=1.0,
                activity_id=activity_id,
                is_used=False,
                expiry_date=expiry_date_str
            )
            db.add(new_credit)

    # 4. Cambiar estado del booking y aplicar cambios
    booking.status = "Cancelled"
    db.commit()
    db.refresh(booking)
    
    return booking