from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.shifts import ShiftTemplateCreate, ShiftTemplateOut
from app.models.shift_template import ShiftTemplate
from app.services import shift_service

router = APIRouter(prefix="/shifts", tags=["shifts"])

@router.get("/templates", response_model=List[ShiftTemplateOut])
def get_templates(db: Session = Depends(get_db)):
    return db.query(ShiftTemplate).all()

@router.post("/templates", response_model=ShiftTemplateOut)
def create_template(data: ShiftTemplateCreate, db: Session = Depends(get_db)):
    new_template = ShiftTemplate(**data.dict())
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    shift_service.create_instances_for_month(db, new_template)
    return new_template

@router.put("/templates/{template_id}", response_model=ShiftTemplateOut)
def update_template(template_id: int, data: ShiftTemplateCreate, db: Session = Depends(get_db)):
    updated = shift_service.update_template_and_recreate_instances(db, template_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Turno base no encontrado")
    return updated

@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    shift_service.delete_template_and_instances(db, template_id)
    return {"message": "Turno base y sus clases eliminadas correctamente"}