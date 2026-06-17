from datetime import timedelta
from sqlalchemy.orm import Session
from ..models.credit import Credit
from ..time_override import business_utcnow
from fastapi import HTTPException, status
from datetime import datetime, date 
from ..time_override import business_today

def consumir_credito_individual(db: Session, credit_id: int, user_id: int, activity_id: int):
    """
    Valida y consume un token de crédito individual único.
    Cambia su estado a usado y deja su amount en 0.0.
    """
    credit = db.query(Credit).filter(Credit.id == credit_id).first()
    
    if not credit:
        raise HTTPException(status_code=404, detail="El crédito especificado no existe.")
        
    if credit.user_id != user_id:
        raise HTTPException(status_code=403, detail="Este crédito no te pertenece.")
        
    if credit.is_used:
        raise HTTPException(status_code=400, detail="Este crédito ya fue utilizado.")
        
    if credit.activity_id != activity_id:
        raise HTTPException(status_code=400, detail="Este crédito no corresponde a esta actividad.")
        
    hoy_local = business_today()  
    
    if credit.expiry_date:
        if isinstance(credit.expiry_date, str):
            fecha_vencimiento = datetime.strptime(credit.expiry_date, "%Y-%m-%d").date()
        elif isinstance(credit.expiry_date, datetime):
            fecha_vencimiento = credit.expiry_date.date()
        else:
            fecha_vencimiento = credit.expiry_date 

        if fecha_vencimiento < hoy_local:
            raise HTTPException(status_code=400, detail="El crédito se encuentra vencido.")

    credit.is_used = True
    credit.amount = 0.0

def otorgar_credito_individual(db: Session, user_id: int, activity_id: int) -> Credit:
    """
    Genera un token de crédito único e individual (una nueva fila en la DB)
    con vencimiento a los 30 días corridos desde su creación.
    """
    ahora_simulado = business_utcnow()
    
    fecha_vencimiento = ahora_simulado + timedelta(days=30)
    expiry_date_str = fecha_vencimiento.strftime("%Y-%m-%d")

    nuevo_credito = Credit(
        user_id=user_id,
        amount=1.0,         
        activity_id=activity_id,
        is_used=False,
        expiry_date=expiry_date_str
    )
    
    db.add(nuevo_credito)
    return nuevo_credito