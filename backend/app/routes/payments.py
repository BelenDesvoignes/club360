from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.services import payment_service
from app.schemas.payment import PaymentResponse

router = APIRouter()

@router.get("/user/{user_id}", response_model=List[PaymentResponse])
def get_user_payments(user_id: int, db: Session = Depends(get_db)):
    """
    Endpoint para que el socio vea su historial de pagos.
    """
    payments = payment_service.get_payments_by_user(db, user_id)
    # Si no hay pagos, devolvemos una lista vacía (es un resultado válido)
    return payments