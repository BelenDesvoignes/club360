from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models.booking import Booking
from ..models.payment import Payment
from ..models.shift_instance import ShiftInstance
from ..models.shift_template import ShiftTemplate
from ..models.subscription import Subscription
from ..models.suspension import Suspension
from ..time_override import business_today, business_utcnow


SUSPENSION_ABONO = "SUSPENSION_ABONO"
PERDIDA_20 = "PERDIDA_20"
ACTIVE_SUSPENSION_STATUS = "active"


def _has_active_activity_suspension(
    db: Session,
    *,
    user_id: int,
    reason: str,
    activity_id: int | None,
) -> bool:
    if activity_id is None:
        return False

    return (
        db.query(Suspension)
        .filter(
            and_(
                Suspension.user_id == user_id,
                Suspension.reason == reason,
                Suspension.activity_id == activity_id,
                Suspension.status == ACTIVE_SUSPENSION_STATUS,
                Suspension.end_date == None,
            )
        )
        .first()
        is not None
    )


def last_day_of_month(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _subscription_already_purchased_this_month(db: Session, *, user_id: int, template_id: int, today: date) -> bool:
    existing = (
        db.query(Subscription)
        .filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.template_id == template_id,
                Subscription.status == "active",
                Subscription.purchase_date != None,
            )
        )
        .all()
    )

    for sub in existing:
        if sub.purchase_date and sub.purchase_date.year == today.year and sub.purchase_date.month == today.month:
            return True
    return False


def _previous_month_date_range(today: date) -> tuple[date, date]:
    """Return the inclusive date range for the previous calendar month."""
    first_this_month = date(today.year, today.month, 1)
    last_prev_month = first_this_month - timedelta(days=1)
    first_prev_month = date(last_prev_month.year, last_prev_month.month, 1)
    return first_prev_month, last_prev_month


def _count_cancelled_subscription_bookings_prev_month(
    db: Session, *, user_id: int, template_id: int, today: date
) -> int:
    start_prev, end_prev = _previous_month_date_range(today)

    return (
        db.query(Booking)
        .join(ShiftInstance, Booking.instance_id == ShiftInstance.id)
        .filter(
            and_(
                Booking.user_id == user_id,
                Booking.status == "Cancelled",
                Booking.subscription_id != None,
                ShiftInstance.template_id == template_id,
                ShiftInstance.date >= start_prev,
                ShiftInstance.date <= end_prev,
            )
        )
        .count()
    )


@dataclass
class SubscriptionQuote:
    template_id: int
    valid_to: date
    remaining_classes: int
    base_amount: float
    amount: float
    discount_percent: int
    discount_applied: bool
    pay_now_required: bool
    discount_reason: str
    instances_created: int


def get_subscription_quote(
    db: Session, *, user_id: int, template_id: int, today: date | None = None
) -> SubscriptionQuote:
    today = today or business_today()

    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template no encontrado")

    if _has_active_activity_suspension(
        db,
        user_id=user_id,
        reason=SUSPENSION_ABONO,
        activity_id=template.activity_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No podés reservar abonos para este deporte porque tenés una suspensión activa.",
        )

    valid_to = last_day_of_month(today)

    # IMPORTANT: Instancias se crean desde templates (admin), no desde abonos.
    instances_created = 0

    instances = (
        db.query(ShiftInstance)
        .filter(
            and_(
                ShiftInstance.template_id == template_id,
                ShiftInstance.date >= today,
                ShiftInstance.date <= valid_to,
                ShiftInstance.is_cancelled == False,
            )
        )
        .order_by(ShiftInstance.date.asc())
        .all()
    )

    remaining_classes = len(instances)
    if remaining_classes <= 0:
        raise HTTPException(
            status_code=400,
            detail="No quedan clases disponibles para el abono en este mes. Intentá más adelante.",
        )

    unit_price = float(template.price or 0)
    base_amount = unit_price * remaining_classes
    if base_amount <= 0:
        raise HTTPException(status_code=400, detail="No se pudo determinar el precio mensual")

    pay_now_required = today.day >= 11

    discount_percent = 0
    discount_applied = False
    discount_reason = "Sin descuento."

    if today.day >= 15:
        if remaining_classes <= 1:
            discount_reason = "Sin descuento: solo queda una clase disponible."
        else:
            cancelled_prev = _count_cancelled_subscription_bookings_prev_month(
                db, user_id=user_id, template_id=template_id, today=today
            )
            lost_discount = _has_active_activity_suspension(
                db,
                user_id=user_id,
                reason=PERDIDA_20,
                activity_id=template.activity_id,
            )
            if lost_discount or cancelled_prev >= 3:
                discount_reason = "Sin descuento: perdiste el beneficio por 3 cancelaciones previas."
            else:
                discount_percent = 20
                discount_applied = True
                discount_reason = "Descuento 20% aplicado (desde el 15)."
    elif 11 <= today.day <= 14:
        discount_reason = "Sin descuento: entre el 11 y el 14 no aplica descuento."
    else:
        discount_reason = "Sin descuento: entre el 1 y el 10 no aplica descuento."

    amount = base_amount
    if discount_applied:
        amount = round(base_amount * 0.8, 2)
    else:
        amount = round(base_amount, 2)
    base_amount = round(base_amount, 2)

    return SubscriptionQuote(
        template_id=template_id,
        valid_to=valid_to,
        remaining_classes=remaining_classes,
        base_amount=base_amount,
        amount=amount,
        discount_percent=discount_percent,
        discount_applied=discount_applied,
        pay_now_required=pay_now_required,
        discount_reason=discount_reason,
        instances_created=instances_created,
    )


@dataclass
class PurchaseResult:
    subscription_id: int
    valid_to: date
    price_paid: float
    bookings_created: int
    skipped_full: int
    skipped_existing: int
    instances_created: int


def purchase_subscription_and_reserve(
    db: Session, *, user_id: int, template_id: int, today: date | None = None
) -> PurchaseResult:
    today = today or business_today()

    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template no encontrado")

    if _subscription_already_purchased_this_month(db, user_id=user_id, template_id=template_id, today=today):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tienes un abono activo para este horario este mes.",
        )

    quote = get_subscription_quote(db, user_id=user_id, template_id=template_id, today=today)

    valid_to = quote.valid_to
    instances_created = quote.instances_created

    instances = (
        db.query(ShiftInstance)
        .filter(
            and_(
                ShiftInstance.template_id == template_id,
                ShiftInstance.date >= today,
                ShiftInstance.date <= valid_to,
                ShiftInstance.is_cancelled == False,
            )
        )
        .order_by(ShiftInstance.date.asc())
        .all()
    )

    monthly_price = float(quote.amount)

    purchase_dt = business_utcnow()

    subscription = Subscription(
        user_id=user_id,
        template_id=template_id,
        month=today.month,
        status="active",
        price_paid=monthly_price,
        purchase_date=purchase_dt,
        valid_to=valid_to,
    )

    payment = Payment(
        user_id=user_id,
        amount=monthly_price,
        status="completed" if quote.pay_now_required else "pending",
        type="subscription",
        date=purchase_dt,
    )

    try:
        db.add(subscription)
        db.add(payment)
        db.flush()  # get subscription.id

        bookings_created = 0
        skipped_existing = 0
        skipped_full = 0

        for instance in instances:
            existing_booking = (
                db.query(Booking)
                .filter(
                    and_(
                        Booking.user_id == user_id,
                        Booking.instance_id == instance.id,
                        Booking.status != "Cancelled",
                    )
                )
                .first()
            )
            if existing_booking:
                skipped_existing += 1
                continue

            booked_count = (
                db.query(Booking)
                .filter(
                    and_(
                        Booking.instance_id == instance.id,
                        Booking.status != "Cancelled",
                    )
                )
                .count()
            )

            capacity = instance.template.capacity if instance.template else None
            if capacity is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo validar la capacidad del turno para el abono.",
                )

            if booked_count >= capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "No hay cupos disponibles para asegurar el mes completo en este horario "
                        f"(sin cupo el {instance.date})."
                    ),
                )

            db.add(
                Booking(
                    user_id=user_id,
                    instance_id=instance.id,
                    created_at=purchase_dt,
                    status="Confirmed",
                    subscription_id=subscription.id,
                    amount_paid=0,
                    payment_status="paid",
                )
            )
            bookings_created += 1

        db.commit()
        db.refresh(subscription)

        return PurchaseResult(
            subscription_id=subscription.id,
            valid_to=valid_to,
            price_paid=monthly_price,
            bookings_created=bookings_created,
            skipped_full=skipped_full,
            skipped_existing=skipped_existing,
            instances_created=instances_created,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al comprar el abono: {str(e)}")


def suspend_users_for_unpaid_subscriptions(db: Session, *, today: date | None = None) -> dict:
    """Suspend users who had a subscription last month and did not pay this month by day 30.

    Intended to be triggered daily by a cron job calling an admin endpoint.
    """
    today = today or business_today()
    if today.day <= 30:
        return {"suspended": 0, "already_suspended": 0, "skipped": 0}

    # previous month
    prev_year = today.year
    prev_month = today.month - 1
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    # Users that had a real (dated) subscription purchase last month
    prev_users = (
        db.query(Subscription.user_id)
        .filter(
            and_(
                Subscription.purchase_date != None,
                Subscription.purchase_date >= datetime(prev_year, prev_month, 1),
                Subscription.purchase_date < datetime(today.year, today.month, 1),
            )
        )
        .distinct()
        .all()
    )

    suspended = 0
    already_suspended = 0
    skipped = 0

    for (user_id,) in prev_users:
        has_current = (
            db.query(Subscription)
            .filter(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.purchase_date != None,
                    Subscription.purchase_date >= datetime(today.year, today.month, 1),
                )
            )
            .first()
        )
        if has_current:
            skipped += 1
            continue

        existing_susp = (
            db.query(Suspension)
            .filter(
                and_(
                    Suspension.user_id == user_id,
                    Suspension.status == "active",
                    Suspension.end_date == None,
                )
            )
            .first()
        )
        if existing_susp:
            already_suspended += 1
            continue

        db.add(
            Suspension(
                user_id=user_id,
                reason="Suspensión automática por falta de pago del abono mensual (1-30).",
                start_date=business_utcnow(),
                end_date=None,
                status="active",
            )
        )
        suspended += 1

    db.commit()

    return {"suspended": suspended, "already_suspended": already_suspended, "skipped": skipped}


def ensure_user_suspension_if_unpaid(db: Session, *, user_id: int, today: date | None = None) -> bool:
    """Lazy (on-demand) version of the unpaid subscription suspension rule.

    University-friendly approach: run this check when the user interacts with the system
    (e.g. opens booking page or tries to create a booking) instead of relying on a cron.

    Rule: if today is day 31+ and the user purchased a subscription last month but has
    not purchased any subscription this month, create an active Suspension.

    Returns True if a new suspension was created.
    """
    today = today or business_today()
    if today.day <= 30:
        return False

    # previous month
    prev_year = today.year
    prev_month = today.month - 1
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    start_prev = datetime(prev_year, prev_month, 1)
    start_this = datetime(today.year, today.month, 1)

    had_prev = (
        db.query(Subscription)
        .filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.purchase_date != None,
                Subscription.purchase_date >= start_prev,
                Subscription.purchase_date < start_this,
            )
        )
        .first()
    )
    if not had_prev:
        return False

    has_current = (
        db.query(Subscription)
        .filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.purchase_date != None,
                Subscription.purchase_date >= start_this,
            )
        )
        .first()
    )
    if has_current:
        return False

    existing_susp = (
        db.query(Suspension)
        .filter(
            and_(
                Suspension.user_id == user_id,
                Suspension.status == "active",
                Suspension.end_date == None,
            )
        )
        .first()
    )
    if existing_susp:
        return False

    db.add(
        Suspension(
            user_id=user_id,
            reason="Suspensión automática por falta de pago del abono mensual (1-30).",
            start_date=business_utcnow(),
            end_date=None,
            status="active",
        )
    )
    db.commit()
    return True


def purchase_half_month_subscription_and_reserve(
    db: Session, *, user_id: int, template_id: int, today: date | None = None
) -> PurchaseResult:
    today = today or business_today()

    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template no encontrado")

    if _subscription_already_purchased_this_month(db, user_id=user_id, template_id=template_id, today=today):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tenés un abono activo para este horario este mes.",
        )

    valid_to = last_day_of_month(today)

    # IMPORTANT: Instancias se crean desde templates (admin), no desde abonos.

    # Traer TODAS las instancias del mes ordenadas por fecha
    all_instances = (
        db.query(ShiftInstance)
        .filter(
            and_(
                ShiftInstance.template_id == template_id,
                ShiftInstance.date >= date(today.year, today.month, 1),
                ShiftInstance.date <= valid_to,
                ShiftInstance.is_cancelled == False,
            )
        )
        .order_by(ShiftInstance.date.asc())
        .all()
    )

    if len(all_instances) < 2:
        raise HTTPException(
            status_code=400,
            detail="No hay suficientes turnos en el mes para registrar un abono a mitad de mes.",
        )

    # Solo las 2 últimas instancias
    instances = all_instances[-2:]

    # Precio: 80% del abono completo (price * 4 * 0.8)
    monthly_full_price = float(template.price or 0) * 4
    half_month_price = round(monthly_full_price * 0.8, 2)

    if half_month_price <= 0:
        raise HTTPException(status_code=400, detail="No se pudo determinar el precio del abono.")

    purchase_dt = business_utcnow()

    subscription = Subscription(
        user_id=user_id,
        template_id=template_id,
        month=today.month,
        status="active",
        price_paid=half_month_price,
        purchase_date=purchase_dt,
        valid_to=valid_to,
    )

    payment = Payment(
        user_id=user_id,
        amount=half_month_price,
        status="completed",
        type="subscription",
        date=purchase_dt,
    )

    try:
        db.add(subscription)
        db.add(payment)
        db.flush()

        bookings_created = 0
        skipped_existing = 0
        skipped_full = 0

        for instance in instances:
            existing_booking = (
                db.query(Booking)
                .filter(
                    and_(
                        Booking.user_id == user_id,
                        Booking.instance_id == instance.id,
                        Booking.status != "Cancelled",
                    )
                )
                .first()
            )
            if existing_booking:
                skipped_existing += 1
                continue

            booked_count = (
                db.query(Booking)
                .filter(
                    and_(
                        Booking.instance_id == instance.id,
                        Booking.status != "Cancelled",
                    )
                )
                .count()
            )

            if booked_count >= instance.capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No hay cupos disponibles para el turno del {instance.date}.",
                )

            db.add(
                Booking(
                    user_id=user_id,
                    instance_id=instance.id,
                    created_at=purchase_dt,
                    status="Confirmed",
                    subscription_id=subscription.id,
                    amount_paid=half_month_price,
                    payment_status="paid",
                )
            )
            bookings_created += 1

        db.commit()
        db.refresh(subscription)

        return PurchaseResult(
            subscription_id=subscription.id,
            valid_to=valid_to,
            price_paid=half_month_price,
            bookings_created=bookings_created,
            skipped_full=skipped_full,
            skipped_existing=skipped_existing,
            instances_created=0,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al comprar el abono: {str(e)}")
