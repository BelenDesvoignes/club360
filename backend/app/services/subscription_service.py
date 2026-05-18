from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.payment import Payment
from app.models.shift_instance import ShiftInstance
from app.models.shift_template import ShiftTemplate
from app.models.subscription import Subscription
from app.models.suspension import Suspension


DAYS_MAP = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Miercoles": 2,
    "Jueves": 3,
    "Viernes": 4,
    "Sábado": 5,
    "Sabado": 5,
    "Domingo": 6,
}


def last_day_of_month(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def ensure_shift_instances_until(db: Session, template: ShiftTemplate, *, start: date, until: date) -> int:
    """Ensure weekly ShiftInstances exist from start..until inclusive.

    This function only creates missing instances; it never deletes existing ones.
    """
    if until < start:
        return 0

    target_weekday = DAYS_MAP.get(template.day_of_week)
    if target_weekday is None:
        return 0

    existing_dates = {
        row[0]
        for row in db.query(ShiftInstance.date)
        .filter(
            and_(
                ShiftInstance.template_id == template.id,
                ShiftInstance.date >= start,
                ShiftInstance.date <= until,
            )
        )
        .all()
    }

    created = 0
    cursor = start
    while cursor.weekday() != target_weekday:
        cursor += timedelta(days=1)
        if cursor > until:
            return 0

    to_create: list[ShiftInstance] = []
    while cursor <= until:
        if cursor not in existing_dates:
            to_create.append(
                ShiftInstance(
                    template_id=template.id,
                    date=cursor,
                    capacity=template.capacity,
                    is_cancelled=False,
                )
            )
            created += 1
        cursor += timedelta(days=7)

    if to_create:
        db.add_all(to_create)
        db.flush()

    return created


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


@dataclass
class PurchaseResult:
    subscription_id: int
    valid_to: date
    price_paid: float
    bookings_created: int
    skipped_full: int
    skipped_existing: int
    instances_created: int


def purchase_subscription_and_reserve(db: Session, *, user_id: int, template_id: int, today: date | None = None) -> PurchaseResult:
    today = today or date.today()

    if today.day < 1 or today.day > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pago del abono mensual solo se permite entre el día 1 y el 30 de cada mes.",
        )

    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template no encontrado")

    if _subscription_already_purchased_this_month(db, user_id=user_id, template_id=template_id, today=today):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tienes un abono activo para este horario este mes.",
        )

    valid_to = last_day_of_month(today)

    instances_created = ensure_shift_instances_until(db, template, start=today, until=valid_to)

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

    if not instances:
        raise HTTPException(status_code=400, detail="No hay turnos disponibles para calcular el abono mensual.")

    monthly_price = float(template.price or 0) * len(instances)
    if monthly_price <= 0:
        raise HTTPException(status_code=400, detail="No se pudo determinar el precio mensual")

    purchase_dt = datetime.utcnow()

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
        status="completed",
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
                    detail=f"No hay cupos disponibles para asegurar el mes completo en este horario (sin cupo el {instance.date}).",
                )

            db.add(
                Booking(
                    user_id=user_id,
                    instance_id=instance.id,
                    status="Confirmed",
                    subscription_id=subscription.id,
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
    today = today or date.today()
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
                start_date=datetime.utcnow(),
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
    today = today or date.today()
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
            start_date=datetime.utcnow(),
            end_date=None,
            status="active",
        )
    )
    db.commit()
    return True
