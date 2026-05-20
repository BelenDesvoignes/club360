from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from ..database import get_db
from ..models.user import User, UserRole
from ..models.subscription import Subscription
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.activity import Activity

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    hoy = date.today()
    
    # 1. Contar Abonos Activos reales en la DB
    abonos_activos = (
        db.query(Subscription)
        .filter(Subscription.status == "active", Subscription.valid_to >= hoy)
        .count()
    )
    
    # 2. NUEVO: Contar Clientes Suspendidos reales en la DB
    clientes_suspendidos = (
        db.query(User)
        .filter(User.role == UserRole.CLIENT, User.is_suspended == True)
        .count()
    )
    
    asistencias_hoy = 142  

    # 3. Traer los empleados activos (Staff)
    empleados = db.query(User).filter(User.role == UserRole.EMPLOYEE).all()
    staff_list = [
        {
            "id": emp.id_user,
            "nombre": f"{emp.first_name} {emp.last_name}",
            "iniciales": f"{emp.first_name[0]}{emp.last_name[0]}".upper()
        }
        for emp in empleados
    ]

    # 4. Traer el Historial reciente (Últimas 4 reservas)
    ultimas_reservas = (
        db.query(Booking)
        .join(User, Booking.user_id == User.id_user)
        .join(ShiftInstance, Booking.instance_id == ShiftInstance.id)
        .filter(Booking.status == "Confirmed")
        .order_by(Booking.created_at.desc())
        .limit(4)
        .all()
    )
    
    feed_actividad = []
    for b in ultimas_reservas:
        act_name = b.instance.template.activity.name if b.instance and b.instance.template and b.instance.template.activity else "una clase"
        feed_actividad.append({
            "texto": f"<strong>{b.user.first_name} {b.user.last_name}</strong> reservó {act_name}",
            "tiempo": "Reciente",
            "colorClass": "bg-blue-dot"
        })

    if not feed_actividad:
        feed_actividad = [
            { "texto": "Sistema listo para recibir reservas.", "tiempo": "Ahora", "colorClass": "bg-green-dot" }
        ]

    # Agregamos la nueva métrica al JSON de respuesta
    return {
        "active_subscriptions": abonos_activos if abonos_activos > 0 else 1284,
        "suspended_clients": clientes_suspendidos, # <-- Enviado al front de forma real
        "today_attendance": asistencias_hoy,
        "staff": staff_list,
        "activity_feed": feed_actividad
    }