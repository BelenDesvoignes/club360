from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..auth_utils import get_user_id_from_token
from ..database import get_db
from ..models.card import Card
from ..schemas.card import CardOut, CardUpsert


router = APIRouter(prefix="/cards", tags=["cards"])


def _extract_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    return user_id


@router.get("/me", response_model=CardOut | None)
def get_my_card(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user_id = _extract_user_id(authorization)
    return (
        db.query(Card)
        .filter(Card.user_id == user_id)
        .order_by(Card.created_at.desc())
        .first()
    )


@router.put("/me", response_model=CardOut)
def upsert_my_card(
    data: CardUpsert,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_id(authorization)

    try:
        # En este producto manejamos 1 tarjeta por usuario: reemplazamos la existente.
        db.query(Card).filter(Card.user_id == user_id).delete(synchronize_session=False)

        card = Card(
            user_id=user_id,
            card_holder=data.card_holder,
            last_four=data.last_four,
            expiry_date=data.expiry_date,
            brand=data.brand,
            status=data.status,
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return card
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error guardando tarjeta: {exc}")


@router.delete("/me")
def delete_my_cards(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user_id = _extract_user_id(authorization)
    try:
        deleted = db.query(Card).filter(Card.user_id == user_id).delete(synchronize_session=False)
        db.commit()
        return {"deleted": int(deleted)}
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando tarjeta: {exc}")
