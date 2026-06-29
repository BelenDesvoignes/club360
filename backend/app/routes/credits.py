from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date  

from ..auth_utils import get_user_id_from_token
from ..database import get_db
from ..models.credit import Credit
from ..models.user import User, UserRole
from pydantic import BaseModel, field_validator  

router = APIRouter(prefix="/credits", tags=["credits"])


class CreditOut(BaseModel):
    id: int
    user_id: int
    amount: float
    activity_id: Optional[int]
    activity_name: Optional[str] = None 
    is_used: bool
    expiry_date: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator("expiry_date", mode="before")
    @classmethod
    def serialize_expiry_date(cls, value):
        if isinstance(value, (datetime, date)):
            return value.strftime("%Y-%m-%d")
        return value


class CreditCreate(BaseModel):
    user_id: int
    amount: float
    activity_id: int = 1


@router.get("/me", response_model=list[CreditOut])
def get_my_credits(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    db_credits = (
        db.query(Credit)
        .filter(Credit.user_id == user_id, Credit.is_used == False, Credit.amount > 0)
        .all()
    )

    for credit in db_credits:
        if credit.activity:
            credit.activity_name = credit.activity.name 

    return db_credits


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

    for credit in credits:
        if credit.activity:
            credit.activity_name = credit.activity.name

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

    admin = db.query(User).filter(User.id_user == admin_user_id).first()
    if not admin or admin.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Permiso denegado: solo admin puede crear créditos")
    
    user = db.query(User).filter(User.id_user == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    existing = db.query(Credit).filter(
        Credit.user_id == data.user_id,
        Credit.activity_id == data.activity_id,
        Credit.is_used == False,
    ).first()

    if existing:
        existing.amount += data.amount
        db.commit()
        db.refresh(existing)
        if existing.activity:
            existing.activity_name = existing.activity.name
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
        if credit.activity:
            credit.activity_name = credit.activity.name
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