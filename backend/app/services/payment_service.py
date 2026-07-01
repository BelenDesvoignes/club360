# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportGeneralTypeIssues=false
from datetime import timedelta
from typing import Any, cast

from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from ..models.activity import Activity
from ..models.booking import Booking
from ..models.payment import Payment
from ..models.subscription import Subscription
from ..models.suspension import Suspension
from ..models.user import User
from ..models.waiting_list import WaitingList
from ..time_override import business_utcnow

PENDING_PAYMENT_STATUSES = ("pending", "pendiente", "partial")
PAYABLE_SUSPENSION_REASONS = ("SUSPENSION_ABONO", "SUSPENSION_CLASE_LIBRE")


def _suspension_activity_id(suspension: Suspension) -> int | None:
    value = getattr(suspension, "activity_id", None)
    return int(value) if value is not None else None


def _find_subscription_for_suspension_payment(
    db: Session,
    payment: Payment,
    suspension: Suspension,
) -> Subscription | None:
    activity_id = _suspension_activity_id(suspension)
    payment_date = getattr(payment, "date", None)
    if activity_id is None or payment_date is None:
        return None

    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == suspension.user_id, Subscription.status == "active"
        )
        .order_by(desc(Subscription.purchase_date))
        .all()
    )

    for subscription in subscriptions:
        if not subscription.template:
            continue

        subscription_activity_id = getattr(subscription.template, "activity_id", None)
        if str(subscription_activity_id) != str(activity_id):
            continue

        purchase_date = getattr(subscription, "purchase_date", None)
        if purchase_date is None:
            continue
        if abs((payment_date - purchase_date).total_seconds()) <= 60:
            return subscription

    return None


def _subscription_matches_suspension(
    db: Session, payment: Payment, suspension: Suspension
) -> bool:
    return (
        _find_subscription_for_suspension_payment(db, payment, suspension) is not None
    )


def _find_pending_payment_for_suspension(
    db: Session, suspension: Suspension
) -> Payment | None:
    reason = getattr(suspension, "reason", None)
    payment_type = "subscription" if reason == "SUSPENSION_ABONO" else "booking"
    payments = (
        db.query(Payment)
        .filter(
            Payment.user_id == suspension.user_id,
            Payment.type == payment_type,
            Payment.status.in_(PENDING_PAYMENT_STATUSES),
        )
        .order_by(desc(Payment.date))
        .all()
    )

    if reason == "SUSPENSION_CLASE_LIBRE":
        return payments[0] if payments else None

    for payment in payments:
        if _subscription_matches_suspension(db, payment, suspension):
            return payment
    return None


def _suspension_sport_name(db: Session, suspension: Suspension) -> str:
    activity_id = _suspension_activity_id(suspension)
    if activity_id is None:
        return (
            "Clase libre"
            if getattr(suspension, "reason", None) == "SUSPENSION_CLASE_LIBRE"
            else "Abono mensual"
        )

    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    return str(activity.name) if activity else f"Actividad {activity_id}"


def get_active_suspensions_by_user(db: Session, user_id: int) -> list[dict]:
    try:
        rows = (
            db.execute(
                text(
                    """
                SELECT id, reason, status, start_date, end_date, activity_id
                FROM suspensions
                WHERE user_id = :user_id AND status = 'active'
                ORDER BY start_date DESC
                """
                ),
                {"user_id": user_id},
            )
            .mappings()
            .all()
        )
    except Exception:
        db.rollback()
        rows = (
            db.execute(
                text(
                    """
                SELECT id, reason, status, start_date, end_date
                FROM suspensions
                WHERE user_id = :user_id AND status = 'active'
                ORDER BY start_date DESC
                """
                ),
                {"user_id": user_id},
            )
            .mappings()
            .all()
        )

    suspensions = []
    for row in rows:
        activity_id = row.get("activity_id")
        reason = row.get("reason")
        payment_type = "subscription" if reason == "SUSPENSION_ABONO" else "booking"
        payment_query = db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.type == payment_type,
            Payment.status.in_(PENDING_PAYMENT_STATUSES),
        )
        if reason == "SUSPENSION_ABONO" and activity_id is not None:
            payment_query = payment_query.filter(Payment.activity_id == activity_id)
        payment = payment_query.order_by(desc(Payment.date)).first()

        sport_name = (
            "Clase libre" if reason == "SUSPENSION_CLASE_LIBRE" else "Abono mensual"
        )
        if activity_id is not None:
            activity = db.query(Activity).filter(Activity.id == activity_id).first()
            sport_name = str(activity.name) if activity else f"Actividad {activity_id}"

        suspensions.append(
            {
                "id": row.get("id"),
                "reason": reason,
                "status": row.get("status"),
                "start_date": row.get("start_date"),
                "end_date": row.get("end_date"),
                "activity_id": activity_id,
                "sport_name": sport_name,
                "amount": float(getattr(payment, "amount", 0) or 0),
                "payment_id": getattr(payment, "id", None),
            }
        )

    return suspensions


def _lift_suspension_if_resolved(db: Session, suspension: Suspension) -> None:
    suspension_data = cast(Any, suspension)
    suspension_data.status = "lifted"
    suspension_data.end_date = business_utcnow()

    has_active_suspensions = (
        db.query(Suspension)
        .filter(
            Suspension.user_id == suspension.user_id,
            Suspension.id != suspension.id,
            Suspension.status == "active",
        )
        .first()
        is not None
    )
    if not has_active_suspensions:
        user = db.query(User).filter(User.id_user == suspension.user_id).first()
        if user:
            cast(Any, user).is_suspended = False


def pay_suspension(
    db: Session, user_id: int, suspension_id: int, amount: float | None = None
) -> Payment:
    from fastapi import HTTPException

    try:
        row = (
            db.execute(
                text(
                    """
                SELECT id, reason, status, activity_id
                FROM suspensions
                WHERE id = :suspension_id AND user_id = :user_id AND status = 'active'
                """
                ),
                {"suspension_id": suspension_id, "user_id": user_id},
            )
            .mappings()
            .first()
        )
    except Exception:
        db.rollback()
        row = (
            db.execute(
                text(
                    """
                SELECT id, reason, status
                FROM suspensions
                WHERE id = :suspension_id AND user_id = :user_id AND status = 'active'
                """
                ),
                {"suspension_id": suspension_id, "user_id": user_id},
            )
            .mappings()
            .first()
        )

    if not row or row.get("reason") not in PAYABLE_SUSPENSION_REASONS:
        raise HTTPException(status_code=404, detail="Suspensión activa no encontrada")

    payment_amount = float(amount or 0)
    if payment_amount <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")

    payment = Payment(
        user_id=user_id,
        activity_id=row.get("activity_id"),
        amount=payment_amount,
        status="completed",
        type="suspension",
        date=business_utcnow(),
    )
    db.add(payment)

    db.execute(
        text(
            """
            UPDATE suspensions
            SET status = 'lifted', end_date = :end_date
            WHERE id = :suspension_id AND user_id = :user_id
            """
        ),
        {
            "end_date": business_utcnow(),
            "suspension_id": suspension_id,
            "user_id": user_id,
        },
    )

    active_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM suspensions
            WHERE user_id = :user_id AND status = 'active'
            """
        ),
        {"user_id": user_id},
    ).scalar_one()
    if int(active_count or 0) == 0:
        db.execute(
            text("UPDATE users SET is_suspended = false WHERE id_user = :user_id"),
            {"user_id": user_id},
        )

    db.commit()
    db.refresh(payment)
    return payment


def _mark_subscription_paid(
    db: Session, subscription: Subscription, amount: float
) -> None:
    subscription_data = cast(Any, subscription)
    subscription_data.price_paid = amount
    subscription_data.purchase_date = business_utcnow()

    associated_bookings = (
        db.query(Booking)
        .filter(
            Booking.subscription_id == subscription.id,
            Booking.user_id == subscription.user_id,
        )
        .all()
    )

    paid_per_booking = (
        round(amount / len(associated_bookings), 2) if associated_bookings else 0.0
    )
    for booking in associated_bookings:
        booking_data = cast(Any, booking)
        booking_data.amount_paid = paid_per_booking
        booking_data.payment_status = "paid"
        booking_data.status = "Confirmed"


def get_payments_by_user(db: Session, user_id: int):
    """
    Busca los pagos del usuario usando la información directa de payments.
    """
    payments = db.query(Payment).filter(Payment.user_id == user_id).all()

    for payment in payments:
        payment_data = cast(Any, payment)
        payment_type = getattr(payment, "type", None)
        activity_id = getattr(payment, "activity_id", None)

        payment_data.activity_id = activity_id
        payment_data.sport_name = None

        if payment_type in ["refund_partial", "refund_total"]:
            payment_data.sport_name = "Devolución"
            continue

        if activity_id is not None:
            activity = db.query(Activity).filter(Activity.id == activity_id).first()
            if activity:
                payment_data.sport_name = getattr(activity, "name", None)

        if not payment_data.sport_name:
            if payment_type in ["subscription", "suscripcion", "Subscription"]:
                payment_data.sport_name = "Abono Mensual"
            elif payment_type == "booking":
                payment_data.sport_name = "Clase Deportiva"

    return payments


def complete_latest_booking_payment(
    db: Session, user_id: int, amount: float
) -> Payment:
    return complete_booking_payment(db, user_id, amount, booking_id=None)


def complete_booking_payment(
    db: Session, user_id: int, amount: float, booking_id: int | None = None
) -> Payment:
    booking = None
    if booking_id is not None:
        booking = (
            db.query(Booking)
            .filter(Booking.id == booking_id, Booking.user_id == user_id)
            .first()
        )

    payment = None
    if booking is not None and booking.created_at is not None:
        window_start = booking.created_at - timedelta(minutes=10)
        window_end = booking.created_at + timedelta(minutes=10)
        payment = (
            db.query(Payment)
            .filter(
                Payment.user_id == user_id,
                Payment.type == "booking",
                Payment.status == "pending",
                Payment.date >= window_start,
                Payment.date <= window_end,
            )
            .order_by(desc(Payment.date))
            .first()
        )

    if not payment:
        payment = (
            db.query(Payment)
            .filter(
                Payment.user_id == user_id,
                Payment.type == "booking",
                Payment.status == "pending",
            )
            .order_by(desc(Payment.date))
            .first()
        )

    if not payment:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            status="completed",
            type="booking",
            date=business_utcnow(),
        )
        db.add(payment)
    else:
        payment_data = cast(Any, payment)
        payment_data.amount = amount
        payment_data.status = "completed"

    if booking is None:
        booking = (
            db.query(Booking)
            .filter(Booking.user_id == user_id, Booking.status == "Pending")
            .order_by(desc(Booking.created_at))
            .first()
        )

    if booking is not None:
        payment_data = cast(Any, payment)
        booking_data = cast(Any, booking)
        payment_data.booking_id = booking.id

        total_price = None
        try:
            if (
                booking.instance
                and booking.instance.template
                and booking.instance.template.price is not None
            ):
                total_price = float(booking.instance.template.price)
        except Exception:
            total_price = None

        current_paid = float(getattr(booking, "amount_paid", 0) or 0)
        new_paid = round(current_paid + float(amount), 2)

        if total_price is not None and total_price > 0:
            if new_paid >= total_price:
                booking_data.amount_paid = total_price
                booking_data.payment_status = "paid"
                booking_data.status = "Confirmed"
            else:
                booking_data.amount_paid = new_paid
                booking_data.payment_status = "partial"
                booking_data.status = "Confirmed"
        else:
            booking_data.amount_paid = new_paid
            if getattr(booking, "status", None) == "Pending":
                booking_data.status = "Confirmed"

        waitlist_entry = (
            db.query(WaitingList)
            .filter(
                WaitingList.user_id == booking.user_id,
                WaitingList.instance_id == booking.instance_id,
                WaitingList.status == "accepted_pending_payment",
            )
            .order_by(WaitingList.promoted_at.desc())
            .first()
        )
        if waitlist_entry:
            waitlist_data = cast(Any, waitlist_entry)
            waitlist_data.status = "promoted"
            waitlist_data.promotion_token = None
            waitlist_data.promotion_expires_at = None

    db.commit()
    db.refresh(payment)
    return payment


def complete_subscription_payment_flow(
    db: Session, user_id: int, payment_id: int
) -> Payment:
    """
    Liquida deudas de abonos mensuales y levanta suspensiones de abono activas.
    """
    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == user_id,
            Payment.type == "subscription",
            Payment.status.in_(PENDING_PAYMENT_STATUSES),
        )
        .first()
    )

    if not payment:
        return complete_booking_payment(db, user_id, 0.0, booking_id=payment_id)

    payment_amount = float(getattr(payment, "amount", 0) or 0)
    if payment_amount <= 0:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Monto inválido")

    payment_data = cast(Any, payment)
    payment_data.status = "completed"
    payment_data.date = business_utcnow()

    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id, Subscription.status == "active")
        .order_by(desc(Subscription.purchase_date))
        .first()
    )
    if subscription:
        _mark_subscription_paid(db, subscription, payment_amount)

    db.commit()
    db.refresh(payment)
    return payment
