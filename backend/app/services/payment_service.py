from sqlalchemy.orm import Session
from app.models.payment import Payment
from sqlalchemy import desc

def get_payments_by_user(db: Session, user_id: int):
    """
    Busca en la base de datos todos los registros de la tabla 'payments'
    que pertenezcan al socio (id_user).
    """
    return db.query(Payment).filter(Payment.user_id == user_id).all()


def complete_latest_booking_payment(db: Session, user_id: int, amount: float) -> Payment:
    payment = (
        db.query(Payment)
        .filter(Payment.user_id == user_id, Payment.type == "booking", Payment.status == "pending")
        .order_by(desc(Payment.date))
        .first()
    )

    if not payment:
        payment = Payment(user_id=user_id, amount=amount, status="completed", type="booking")
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    payment.amount = amount
    payment.status = "completed"
    db.commit()
    db.refresh(payment)
    return payment