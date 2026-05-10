from sqlalchemy.orm import Session
from app.models.payment import Payment

def get_payments_by_user(db: Session, user_id: int):
    """
    Busca en la base de datos todos los registros de la tabla 'payments'
    que pertenezcan al socio (id_user).
    """
    return db.query(Payment).filter(Payment.user_id == user_id).all()