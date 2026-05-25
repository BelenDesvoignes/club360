from sqlalchemy.orm import Session
from ..models.payment import Payment
from ..models.booking import Booking
from sqlalchemy import desc
from datetime import timedelta

def get_payments_by_user(db: Session, user_id: int):
    """
    Busca en la base de datos todos los registros de la tabla 'payments'
    que pertenezcan al socio (id_user).
    """
    return db.query(Payment).filter(Payment.user_id == user_id).all()


def complete_latest_booking_payment(db: Session, user_id: int, amount: float) -> Payment:
    return complete_booking_payment(db, user_id, amount, booking_id=None)


def complete_booking_payment(db: Session, user_id: int, amount: float, booking_id: int | None = None) -> Payment:
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
            .filter(Payment.user_id == user_id, Payment.type == "booking", Payment.status == "pending")
            .order_by(desc(Payment.date))
            .first()
        )

    if not payment:
        payment = Payment(user_id=user_id, amount=amount, status="completed", type="booking")
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
        # Update booking payment fields
        total_price = None
        try:
            if booking.instance and booking.instance.template and booking.instance.template.price is not None:
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
                # paying a deposit confirms the booking spot
                booking.status = "Confirmed"
        else:
            # Fallback: keep previous semantics but ensure confirmed if payment was completed
            booking.amount_paid = new_paid
            if booking.status == "Pending":
                booking.status = "Confirmed"

    db.commit()
    db.refresh(payment)
    return payment