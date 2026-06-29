from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..services import payment_service
from ..schemas.payment import PaymentCompleteBookingRequest, PaymentResponse
from ..auth_utils import get_user_id_from_token

router = APIRouter()


def _extract_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return user_id

@router.get("/user/{user_id}", response_model=List[PaymentResponse])
def get_user_payments(user_id: int, db: Session = Depends(get_db)):
    """
    Endpoint para que el socio vea su historial de pagos.
    """
    payments = payment_service.get_payments_by_user(db, user_id)
    # Si no hay pagos, devolvemos una lista vacía (es un resultado válido)
    return payments


@router.post("/me/complete-booking", response_model=PaymentResponse)
def complete_booking_payment(
    payload: PaymentCompleteBookingRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_id(authorization)

    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")

    return payment_service.complete_booking_payment(
        db,
        user_id,
        float(payload.amount),
        booking_id=payload.booking_id,
    )

@router.post("/me/complete-subscription/{payment_id}", response_model=PaymentResponse)
def complete_subscription_payment_route(
    payment_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Endpoint dedicado para liquidar deudas de Abonos Mensuales de forma diferida.
    Actualiza el pago, la suscripción y todas sus clases hijas.
    """
    user_id = _extract_user_id(authorization)
    return payment_service.complete_subscription_payment_flow(db, user_id, payment_id)