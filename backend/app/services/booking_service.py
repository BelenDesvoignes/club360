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


SUSPENSION_ABONO = "SUSPENSION_ABONO"
SUSPENSION_CLASE_LIBRE = "SUSPENSION_CLASE_LIBRE"
PERDIDA_20 = "PERDIDA_20"
ACTIVE_SUSPENSION_STATUS = "active"
LIFTED_SUSPENSION_STATUS = "lifted"


def get_active_suspension(
    db: Session,
    user_id: int,
    reason: str,
    activity_id: int | None = None,
) -> Suspension | None:
    filters = [
        Suspension.user_id == user_id,
        Suspension.reason == reason,
        Suspension.status == ACTIVE_SUSPENSION_STATUS,
        Suspension.end_date == None,
    ]

    # If activity_id is provided, the suspension must match that sport/activity.
    # NULL activity_id is kept harmless for legacy/demo rows and does not block
    # activity-specific checks.
    if activity_id is not None:
        filters.append(Suspension.activity_id == activity_id)

    return db.query(Suspension).filter(and_(*filters)).first()


def has_active_suspension(
    db: Session,
    user_id: int,
    reason: str,
    activity_id: int | None = None,
) -> bool:
    return get_active_suspension(db, user_id, reason, activity_id=activity_id) is not None


def is_user_suspended(db: Session, user_id: int) -> bool:
    """Check if user has an active blocking suspension."""
    suspension = (
        db.query(Suspension)
        .filter(
            and_(
                Suspension.user_id == user_id,
                Suspension.reason.in_([SUSPENSION_ABONO, SUSPENSION_CLASE_LIBRE]),
                Suspension.status == ACTIVE_SUSPENSION_STATUS,
                Suspension.end_date == None,
            )
        )
        .first()
    )
    return suspension is not None


def create_subscription_booking(db: Session, user_id: int, template_id: int) -> dict:
    """Simplified university/demo flow for booking an abono.

    SUSPENSION_ABONO blocks the operation.
    PERDIDA_20 does not block, but removes the 20% discount from day 15 onward.
    """
    user = db.query(User).filter(User.id_user == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    from ..models.shift_template import ShiftTemplate

    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Abono/clase base no encontrada")

    activity_id = template.activity_id
    if has_active_suspension(db, user_id, SUSPENSION_ABONO, activity_id=activity_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No podés reservar abonos para este deporte porque tenés una suspensión activa.",
        )

    base_price = float(template.price or 0)
    today = business_today()
    has_lost_discount = has_active_suspension(db, user_id, PERDIDA_20)
    discount_applied = today.day >= 15 and not has_lost_discount
    amount_to_charge = round(base_price * 0.8, 2) if discount_applied else base_price

    subscription = Subscription(
        user_id=user_id,
        template_id=template_id,
        month=today.month,
        status="active",
        price_paid=None,
        purchase_date=business_utcnow(),
        valid_to=None,
    )
    db.add(subscription)
    db.flush()

    payment = Payment(
        user_id=user_id,
        amount=amount_to_charge,
        status="pending",
        type="subscription",
        date=business_utcnow(),
    )
    db.add(payment)
    db.commit()
    db.refresh(subscription)
    db.refresh(payment)

    return {
        "message": "Abono reservado. Pago pendiente generado.",
        "subscription_id": subscription.id,
        "payment_id": payment.id,
        "base_price": base_price,
        "amount_to_charge": amount_to_charge,
        "discount_applied": discount_applied,
        "lost_discount_by_perdida_20": has_lost_discount,
    }


def create_free_class_booking(db: Session, user_id: int, instance_id: int) -> Booking:
    """Simplified university/demo flow for booking a clase libre."""
    if has_active_suspension(db, user_id, SUSPENSION_CLASE_LIBRE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No podés reservar clases libres porque tenés una suspensión activa para clases libres.",
        )

    return create_booking(db, user_id=user_id, instance_id=instance_id, subscription_id=None)


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

    # Rule 1: for clase libre, only SUSPENSION_CLASE_LIBRE blocks.
    # SUSPENSION_ABONO blocks abonos only; PERDIDA_20 never blocks.
    if has_active_suspension(db, user_id, SUSPENSION_CLASE_LIBRE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No podés reservar clases libres porque tenés una suspensión activa para clases libres."
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
    Cancela una reserva aplicando límites diferenciados:
    - Si es abono -> Verifica 48hs para devolver crédito.
    - Si es clase suelta -> Verifica 24hs para procesar reembolso.
    """
    from ..models.user import UserRole
    from .credit_service import otorgar_credito_individual
    from .refund_service import procesar_reembolso_clase_suelta
    from datetime import datetime, timedelta
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    user = db.query(User).filter(User.id_user == user_id).first()
    if booking.user_id != user_id and (not user or user.role != UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
        
    if booking.status == "Cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya cancelada")

    instance = db.query(ShiftInstance).filter(ShiftInstance.id == booking.instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    class_datetime = business_utcnow()
    if instance.date and instance.template and instance.template.start_time:
        try:
            time_parts = list(map(int, instance.template.start_time.split(":")))
            class_datetime = datetime.combine(instance.date, datetime.min.time().replace(hour=time_parts[0], minute=time_parts[1]))
        except Exception:
            class_datetime = datetime.combine(instance.date, datetime.min.time())

    time_difference = class_datetime - business_utcnow()

    if booking.subscription_id is not None:
        if time_difference >= timedelta(hours=48):
            activity_id = instance.template.activity_id if instance.template else 1
            otorgar_credito_individual(db, booking.user_id, activity_id)
    else:
        if time_difference >= timedelta(hours=24):
            procesar_reembolso_clase_suelta(db, booking, instance)

    booking.status = "Cancelled"
    db.commit()
    db.refresh(booking)
    
    from .waiting_list_service import WaitingListService
    WaitingListService.process_waiting_list_on_cancellation(db, instance_id=booking.instance_id)

    return booking

def create_booking_with_credit(db: Session, user_id: int, instance_id: int, credit_id: int) -> Booking:
    """
    Crea una reserva confirmada utilizando un token de crédito individual único.
    """
    from .credit_service import consumir_credito_individual

    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Clase no encontrada.")
        
    if instance.date < business_today():
        raise HTTPException(status_code=400, detail="No podés reservar clases pasadas.")

    # 3. Validar capacidad del turno
    if not has_instance_capacity(db, instance_id):
        raise HTTPException(status_code=400, detail="No hay cupos disponibles para esta clase.")

    existing = db.query(Booking).filter(
        and_(
            Booking.user_id == user_id,
            Booking.instance_id == instance_id,
            Booking.status != "Cancelled"
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya tenés una reserva activa para esta clase.")

    activity_id = instance.template.activity_id if instance.template else 1
    consumir_credito_individual(db, credit_id=credit_id, user_id=user_id, activity_id=activity_id)

    booking = Booking(
        user_id=user_id,
        instance_id=instance_id,
        created_at=business_utcnow(),
        status="Confirmed",
        subscription_id=None,
        amount_paid=0.0,
        payment_status="paid"  
    )
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    return booking