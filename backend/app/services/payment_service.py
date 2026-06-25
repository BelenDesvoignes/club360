# pyright: reportGeneralTypeIssues=false, reportAssignmentType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportOperatorIssue=false

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, text
from datetime import timedelta

# Modelos de la base de datos
from ..models.payment import Payment
from ..models.booking import Booking
from ..models.subscription import Subscription
from ..models.shift_template import ShiftTemplate
from ..models.suspension import Suspension
from ..models.user import User
from fastapi import HTTPException

# Utilitario del tiempo del sistema
from ..time_override import business_utcnow


def get_payments_by_user(db: Session, user_id: int):
    """
    Busca los pagos del usuario e inyecta el deporte real original
    utilizando únicamente las columnas reales de la base de datos (instance_id).
    """
    payments = db.query(Payment).filter(Payment.user_id == user_id).all()

    for payment in payments:
        payment.sport_name = None

        # 🌟 Si es una devolución, salteamos la búsqueda por tiempo
        if payment.type in ["refund_partial", "refund_total"]:
            payment.sport_name = "Devolución"
            continue

        activity_id = getattr(payment, "activity_id", None)
        if activity_id:
            result = db.execute(
                text("SELECT name FROM activities WHERE id = :activity_id"),
                {"activity_id": activity_id},
            ).fetchone()
            if result and result[0]:
                payment.sport_name = result[0]
                continue

        if payment.type == "booking":
            try:
                b_id = getattr(
                    payment, "booking_id", getattr(payment, "id_booking", None)
                )

                if b_id:
                    # SQL Corregido: Limpiamos el OR b.id_instance erróneo
                    query_sql = text("""
                        SELECT a.name 
                        FROM bookings b
                        JOIN shift_instances i ON b.instance_id = i.id
                        JOIN shift_templates t ON i.template_id = t.id
                        JOIN activities a ON t.activity_id = a.id
                        WHERE b.id = :booking_id
                    """)
                    result = db.execute(query_sql, {"booking_id": b_id}).fetchone()
                else:
                    # SQL Corregido: Limpiamos el OR b.id_instance erróneo
                    query_sql = text("""
                        SELECT a.name 
                        FROM bookings b
                        JOIN shift_instances i ON b.instance_id = i.id
                        JOIN shift_templates t ON i.template_id = t.id
                        JOIN activities a ON t.activity_id = a.id
                        WHERE b.user_id = :user_id 
                          AND b.status != 'Cancelled'
                          AND b.created_at <= :payment_date
                        ORDER BY b.created_at DESC
                        LIMIT 1
                    """)
                    result = db.execute(
                        query_sql, {"user_id": user_id, "payment_date": payment.date}
                    ).fetchone()

                if result and result[0]:
                    payment.sport_name = result[0]
                else:
                    payment.sport_name = "Clase Deportiva"

            except Exception as e:
                db.rollback()
                print(f"Error al recuperar deporte real por SQL: {str(e)}")
                payment.sport_name = "Clase Deportiva"

        elif payment.type in ["subscription", "suscripcion", "Subscription"]:
            payment.sport_name = "Abono Mensual"

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
        payment.amount = amount
        payment.status = "completed"

    if booking is None:
        booking = (
            db.query(Booking)
            .filter(Booking.user_id == user_id, Booking.status == "Pending")
            .order_by(desc(Booking.created_at))
            .first()
        )

    if booking is not None:
        # 🌟 FIJAMOS EL ENLACE: Guardamos explícitamente el booking_id en el pago
        payment.booking_id = booking.id
        if booking.instance and booking.instance.template:
            payment.activity_id = booking.instance.template.activity_id

        # Update booking payment fields
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

        current_paid = float(booking.amount_paid or 0)
        new_paid = round(current_paid + float(amount), 2)

        if total_price is not None and total_price > 0:
            if new_paid >= total_price:
                booking.amount_paid = total_price
                booking.payment_status = "paid"
                booking.status = "Confirmed"
            else:
                booking.amount_paid = new_paid
                booking.payment_status = "partial"
                booking.status = "Confirmed"
        else:
            booking.amount_paid = new_paid
            if booking.status == "Pending":
                booking.status = "Confirmed"

    db.commit()
    db.refresh(payment)
    return payment


def get_payable_suspensions_by_user(db: Session, user_id: int) -> list[dict]:
    """Returns active suspensions that the user can see/pay from Mis Pagos."""
    fine_amount_by_reason = {
        "SUSPENSION_ABONO": 5000.0,
        "SUSPENSION_CLASE_LIBRE": 5000.0,
        "PERDIDA_20": 0.0,
    }

    suspensions = (
        db.query(Suspension)
        .filter(
            Suspension.user_id == user_id,
            Suspension.status == "active",
            Suspension.end_date == None,
        )
        .order_by(Suspension.start_date.desc())
        .all()
    )

    return [
        {
            "id": suspension.id,
            "reason": suspension.reason,
            "activity_id": suspension.activity_id,
            "status": suspension.status,
            "start_date": suspension.start_date,
            "end_date": suspension.end_date,
            "amount_due": fine_amount_by_reason.get(suspension.reason, 5000.0),
        }
        for suspension in suspensions
    ]


def pay_suspension_fine(
    db: Session, user_id: int, suspension_id: int, amount: float = 0.0
) -> dict:
    """Marks one specific suspension as paid/inactive.

    After lifting that suspension, the user's is_suspended flag is cleared only when
    there are no other active suspensions at the same time.
    """
    suspension = (
        db.query(Suspension)
        .filter(Suspension.id == suspension_id, Suspension.user_id == user_id)
        .first()
    )
    if not suspension:
        raise HTTPException(status_code=404, detail="Suspensión no encontrada")

    if suspension.status != "active":
        raise HTTPException(status_code=400, detail="Esta suspensión ya no está activa")

    payment = Payment(
        user_id=user_id,
        amount=float(amount or 0.0),
        status="completed",
        type="suspension_fine",
        date=business_utcnow(),
    )
    db.add(payment)

    suspension.status = "desactive"
    suspension.end_date = business_utcnow()

    active_suspensions_count = (
        db.query(Suspension)
        .filter(
            Suspension.user_id == user_id,
            Suspension.status == "active",
            Suspension.end_date == None,
            Suspension.id != suspension_id,
        )
        .count()
    )

    user = db.query(User).filter(User.id_user == user_id).first()
    if user and active_suspensions_count == 0:
        user.is_suspended = False

    db.commit()
    db.refresh(payment)
    db.refresh(suspension)

    return {
        "message": "Multa pagada y suspensión desactivada.",
        "payment_id": payment.id,
        "suspension_id": suspension.id,
        "suspension_status": suspension.status,
        "user_is_suspended": bool(user.is_suspended) if user else None,
        "remaining_active_suspensions": active_suspensions_count,
    }


def complete_subscription_payment_flow(
    db: Session, user_id: int, payment_id: int
) -> Payment:
    """
    Desarrollado para el flujo diferido de Abonos.
    Busca el pago de la suscripción, lo completa, y actualiza en cadena
    el estado del Abono y de todas las clases/reservas que contiene.
    """
    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == user_id,
            Payment.type == "subscription",
        )
        .first()
    )

    if not payment:
        return complete_booking_payment(db, user_id, 0.0, booking_id=payment_id)

    activity_id = getattr(payment, "activity_id", None)
    if activity_id is not None:
        active_suspension = (
            db.query(Suspension)
            .filter(
                and_(
                    Suspension.user_id == user_id,
                    Suspension.reason == "SUSPENSION_ABONO",
                    Suspension.activity_id == activity_id,
                    Suspension.status == "active",
                    Suspension.end_date == None,
                )
            )
            .first()
        )
        if active_suspension:
            raise HTTPException(
                status_code=403,
                detail="Este abono ya generó una suspensión para este deporte. Pagá la suspensión para volver a reservar ese abono.",
            )

    payment.status = "completed"
    payment.date = business_utcnow()

    subscription_query = (
        db.query(Subscription)
        .join(ShiftTemplate, Subscription.template_id == ShiftTemplate.id)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.price_paid == None,
        )
    )
    if activity_id is not None:
        subscription_query = subscription_query.filter(
            ShiftTemplate.activity_id == activity_id
        )

    subscription = subscription_query.order_by(desc(Subscription.purchase_date)).first()

    if subscription:
        subscription.price_paid = float(payment.amount)
        subscription.purchase_date = business_utcnow()

        associated_bookings = (
            db.query(Booking)
            .filter(
                Booking.subscription_id == subscription.id, Booking.user_id == user_id
            )
            .all()
        )

        for booking in associated_bookings:
            booking.amount_paid = (
                round(float(payment.amount) / len(associated_bookings), 2)
                if associated_bookings
                else 0.0
            )
            booking.payment_status = "paid"
            booking.status = "Confirmed"

    db.commit()
    db.refresh(payment)
    return payment
