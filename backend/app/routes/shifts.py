from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.activity import Activity
from sqlalchemy import and_
from app.database import get_db
from app.schemas.shifts import ShiftTemplateCreate, ShiftTemplateOut, ShiftDetailResponse
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

@router.get("/instances")
def get_instances(db: Session = Depends(get_db)):
    from sqlalchemy import func

    active_templates = (
        db.query(ShiftTemplate)
        .join(Activity, ShiftTemplate.activity_id == Activity.id)
        .filter(Activity.is_active == True)
        .filter(ShiftTemplate.is_active == True)
        .all()
    )

    template_ids = [t.id for t in active_templates]
    templates_with_instances = (
        db.query(ShiftTemplate.id)
        .join(ShiftInstance, ShiftInstance.template_id == ShiftTemplate.id)
        .filter(
            ShiftTemplate.id.in_(template_ids),
            ShiftInstance.date >= date.today(),
            ShiftInstance.is_cancelled == False
        )
        .distinct()
        .all()
    )

    existing_template_ids = {t[0] for t in templates_with_instances}
    templates_to_backfill = [t for t in active_templates if t.id not in existing_template_ids]

    for template in templates_to_backfill:
        shift_service.create_instances_for_month(db, template)

    booking_count_sq = (
        db.query(
            Booking.instance_id,
            func.count(Booking.id).label('count')
        )
        .filter(Booking.status != "Cancelled")
        .group_by(Booking.instance_id)
        .subquery()
    )

    result = (
        db.query(
            ShiftInstance.id,
            ShiftInstance.date,
            ShiftInstance.is_cancelled,
            ShiftInstance.capacity.label('instance_capacity'),
            ShiftTemplate.id.label('template_id'),
            ShiftTemplate.activity_id,
            ShiftTemplate.day_of_week,
            ShiftTemplate.start_time,
            ShiftTemplate.capacity.label('template_capacity'),
            ShiftTemplate.price,
            Activity.name.label('activity_name'),
            Activity.court.label('court'),
            func.coalesce(booking_count_sq.c.count, 0).label('booked_count')
        )
        .join(ShiftTemplate, ShiftInstance.template_id == ShiftTemplate.id)
        .join(Activity, ShiftTemplate.activity_id == Activity.id)
        .outerjoin(booking_count_sq, ShiftInstance.id == booking_count_sq.c.instance_id)
        .filter(Activity.is_active == True)
        .filter(ShiftTemplate.is_active == True)
        .filter(ShiftInstance.date >= date.today())
        .filter(ShiftInstance.is_cancelled == False)
        .order_by(ShiftInstance.date.asc(), ShiftTemplate.start_time.asc())
        .all()
    )

    instances_list = []
    for row in result:
        instances_list.append({
            "id": row.id,
            "date": str(row.date),
            "is_cancelled": row.is_cancelled,
            "booked_count": row.booked_count if row.booked_count else 0,
            "activity_name": row.activity_name or f"Actividad {row.activity_id}",
            "court": row.court or "",
            "capacity": row.instance_capacity, 
            "template": {
                "id": row.template_id,
                "activity_id": row.activity_id,
                "day_of_week": row.day_of_week,
                "start_time": row.start_time,
                "capacity": row.template_capacity,
                "price": float(row.price) if row.price else 100.0
            }
        })

    return instances_list

@router.get("/instances/{instance_id}", response_model=ShiftDetailResponse)
def get_shift_instance(instance_id: int, db: Session = Depends(get_db)):
    detail = shift_service.get_shift_instance_detail(db, instance_id)
    if not detail:
        raise HTTPException(status_code=404, detail="El detalle del turno no existe")
    return detail


@router.patch("/instances/{instance_id}")
def update_instance_capacity(instance_id: int, capacity: int, db: Session = Depends(get_db)):
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="La clase específica no existe")
    
    booked_count = db.query(Booking).filter(
        Booking.instance_id == instance_id, 
        Booking.status != "Cancelled"
    ).count()
    
    if capacity < booked_count:
        raise HTTPException(
            status_code=400, 
            detail=f"No puedes bajar el cupo a {capacity} porque ya hay {booked_count} personas anotadas."
        )
    instance.capacity = capacity
    db.commit()
    
    return {"message": "Cupo de la clase actualizado", "new_capacity": instance.capacity}

@router.patch("/instances/{instance_id}/cancel")
def cancel_shift_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="La clase no existe")
    
    instance.is_cancelled = True
    db.commit()
    
    return {"message": "Clase cancelada exitosamente", "id": instance_id}