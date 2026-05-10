from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from ..auth_utils import get_user_id_from_token
from ..database import get_db
from ..models.credit import Credit
from ..models.user import User, UserRole
from pydantic import BaseModel

router = APIRouter(prefix="/credits", tags=["credits"])


class CreditOut(BaseModel):
    id: int
    user_id: int
    amount: float
    activity_id: Optional[int]
    is_used: bool
    expiry_date: Optional[str] = None

    class Config:
        from_attributes = True


class CreditCreate(BaseModel):
    user_id: int
    amount: float
    activity_id: int = 1  # Default a 1 para testing


@router.get("/me", response_model=list[CreditOut])
def get_my_credits(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    return (
        db.query(Credit)
        .filter(Credit.user_id == user_id, Credit.is_used == False, Credit.amount > 0)
        .all()
    )


@router.get("/{user_id}", response_model=list[CreditOut])
def get_user_credits(user_id: int, db: Session = Depends(get_db)):
    """Obtiene todos los créditos disponibles del usuario"""
    user = db.query(User).filter(User.id_user == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    credits = db.query(Credit).filter(
        Credit.user_id == user_id,
        Credit.is_used == False,
        Credit.amount > 0,
    ).all()

    return credits


@router.post("/create", response_model=CreditOut)
def create_credit_admin_only(
    data: CreditCreate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    """SOLO ADMIN: Asigna créditos a un usuario. El cliente NO puede crear sus propios créditos."""
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    admin_user_id = get_user_id_from_token(token)
    if not admin_user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Verificar que el usuario que hace la solicitud sea admin
    admin = db.query(User).filter(User.id_user == admin_user_id).first()
    if not admin or admin.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Permiso denegado: solo admin puede crear créditos")
    
    user = db.query(User).filter(User.id_user == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Si ya existe un crédito sin usar para la misma actividad, sumamos en vez de crear otro registro
    existing = db.query(Credit).filter(
        Credit.user_id == data.user_id,
        Credit.activity_id == data.activity_id,
        Credit.is_used == False,
    ).first()

    if existing:
        existing.amount += data.amount
        db.commit()
        db.refresh(existing)
        return existing

    credit = Credit(
        user_id=data.user_id,
        amount=data.amount,
        activity_id=data.activity_id,
        is_used=False,
    )
    db.add(credit)
    try:
        db.commit()
        db.refresh(credit)
        return credit
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear crédito: {str(e)}")


@router.delete("/{credit_id}")
def delete_credit(credit_id: int, db: Session = Depends(get_db)):
    """Eliminar un crédito (útil para pruebas)."""
    c = db.query(Credit).filter(Credit.id == credit_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
    db.delete(c)
    db.commit()
    return {"message": "Crédito eliminado"}
