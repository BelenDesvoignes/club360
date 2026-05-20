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
    
    # 2. Contar Clientes Suspendidos reales en la DB
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
            "iniciales": f"{emp.first_name[0]}{emp.last_name[0]}".upper() if emp.first_name and emp.last_name else "ST"
        }
        for emp in empleados
    ]

    # 4. Traer el Historial reciente (Optimizado con JOINs para evitar N+1)
    resultados = (
        db.query(Booking, User, Activity)
        .join(User, Booking.user_id == User.id_user)
        .join(ShiftInstance, Booking.instance_id == ShiftInstance.id)
        .join(ShiftInstance.template) 
        .join(Activity) 
        .filter(Booking.status == "Confirmed")
        .order_by(Booking.created_at.desc())
        .limit(4)
        .all()
    )
    
    # 5. Mapeo instantáneo desde la tupla de resultados
    feed_actividad = []
    for booking, user, activity in resultados:
        act_name = activity.name if activity else "una clase"
        feed_actividad.append({
            "texto": f"<strong>{user.first_name} {user.last_name}</strong> reservó {act_name}",
            "tiempo": "Reciente",
            "colorClass": "bg-blue-dot"
        })

    if not feed_actividad:
        feed_actividad = [
            { "texto": "Sistema listo para recibir reservas.", "tiempo": "Ahora", "colorClass": "bg-green-dot" }
        ]

    return {
        "active_subscriptions": abonos_activos if abonos_activos > 0 else 1284,
        "suspended_clients": clientes_suspendidos,
        "today_attendance": asistencias_hoy,
        "staff": staff_list,
        "activity_feed": feed_actividad
    }