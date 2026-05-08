from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.models.shift_instance import ShiftInstance
from app.models.shift_template import ShiftTemplate

def create_instances_for_month(db: Session, template: ShiftTemplate):
    days_map = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6}
    target_day = days_map.get(template.day_of_week)
    if target_day is None: return []

    today = date.today()
    new_instances = []
    for i in range(35):
        check_date = today + timedelta(days=i)
        if check_date.weekday() == target_day:
            db_instance = ShiftInstance(template_id=template.id, date=check_date, is_cancelled=False)
            db.add(db_instance)
            new_instances.append(db_instance)
            if len(new_instances) == 4: break
    db.commit()
    return new_instances

def delete_template_and_instances(db: Session, template_id: int):
    db.query(ShiftInstance).filter(ShiftInstance.template_id == template_id).delete()
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if template:
        db.delete(template)
    db.commit()

def update_template_and_recreate_instances(db: Session, template_id: int, new_data):
    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == template_id).first()
    if not template: return None

    template.day_of_week = new_data.day_of_week
    template.start_time = new_data.start_time
    template.capacity = new_data.capacity
    db.commit()

    db.query(ShiftInstance).filter(ShiftInstance.template_id == template_id, ShiftInstance.date >= date.today()).delete()
    create_instances_for_month(db, template)
    
    return template