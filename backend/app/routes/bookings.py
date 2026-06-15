from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from ..models.shift_instance import ShiftInstance
from ..models.activity import Activity
from ..database import get_db
from ..schemas.bookings import BookingCreate, BookingOut, BookingListOut
from ..models.booking import Booking
from ..models.user import User
from ..services import booking_service
from ..auth_utils import get_user_id_from_token
import datetime
from ..time_override import business_today

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _booking_status(booking: Booking) -> str:
    # Older rows can have a NULL status; keep the API stable for the frontend.
    return booking.status or "Pending"


def _extract_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    return user_id


@router.post("/", response_model=BookingOut)
def create_booking(
    data: BookingCreate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    user_id = _extract_user_id(authorization)
    
    # FIX BLINDADO PARA SOPORTAR RESERVA DE ABONOS (EVITA EL ERROR 422 SI VIAJA NULL)
    inst_id = data.instance_id if (hasattr(data, 'instance_id') and data.instance_id != 0) else None
    sub_id = data.subscription_id if hasattr(data, 'subscription_id') else None

    # Se delega al servicio pasándole los parámetros limpios mapeados desde Pydantic
    booking = booking_service.create_booking(db, user_id=user_id, instance_id=inst_id, subscription_id=sub_id)
    return booking


@router.get("/user/{user_id}", response_model=list[BookingListOut])
def get_user_bookings(user_id: int, db: Session = Depends(get_db)):
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    result = []
    for booking in bookings:
        instance = db.query(ShiftInstance).filter(ShiftInstance.id == booking.instance_id).first()
        activity_name = None
        day_of_week = None
        start_time = None
        booking_date = None
        price = None

        if instance:
            booking_date = instance.date
            day_of_week = instance.template.day_of_week if instance.template else None
            start_time = instance.template.start_time if instance.template else None
            price = float(instance.template.price) if instance.template and instance.template.price is not None else None
            if instance.template and instance.template.activity:
                activity_name = instance.template.activity.name

        result.append({
            "id": booking.id,
            "user_id": booking.user_id,
            "instance_id": booking.instance_id,
            "status": _booking_status(booking),
            "subscription_id": booking.subscription_id,
            "is_subscription": booking.subscription_id is not None,
            "amount_paid": float(booking.amount_paid) if booking.amount_paid is not None else None,
            "payment_status": booking.payment_status,
            "created_at": booking.created_at,
            "activity_name": activity_name,
            "date": booking_date,
            "day_of_week": day_of_week,
            "start_time": start_time,
            "price": price,
        })

    return result


@router.get("/me", response_model=list[BookingListOut])
def get_my_bookings(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user_id = _extract_user_id(authorization)
    return get_user_bookings(user_id, db)


@router.get("/my-next")
def get_my_next_booking(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    from datetime import datetime

    user_id = _extract_user_id(authorization)

    hoy = business_today()
    ahora = datetime.now().strftime("%H:%M")

    bookings = (
        db.query(Booking)
        .filter(
            Booking.user_id == user_id,
            Booking.status != "Cancelled",
        )
        .all()
    )

    proxima = None
    for booking in bookings:
        instance = db.query(ShiftInstance).filter(ShiftInstance.id == booking.instance_id).first()
        if not instance or instance.is_cancelled:
            continue
        if instance.date < hoy:
            continue
        if instance.date == hoy and instance.template and instance.template.start_time < ahora:
            continue

        if proxima is None or instance.date < proxima["date"] or (
            instance.date == proxima["date"] and
            instance.template.start_time < proxima["start_time"]
        ):
            proxima = {
                "booking_id": booking.id,
                "instance_id": instance.id,
                "date": instance.date,
                "start_time": instance.template.start_time if instance.template else None,
                "activity_name": instance.template.activity.name if instance.template and instance.template.activity else None,
            }

    if not proxima:
        return None

    proxima["date"] = str(proxima["date"])
    return proxima


@router.post("/{booking_id}/cancel", response_model=dict)
def cancel_booking(
    booking_id: int, 
    authorization: str | None = Header(default=None), 
    db: Session = Depends(get_db)
):
    """Cancela la reserva delegando la operación de forma segura a la lógica de servicios"""
    user_id = _extract_user_id(authorization)

    try:
        booking_service.cancel_booking(db, booking_id, user_id)
        return {"message": "Reserva cancelada exitosamente"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar la cancelación: {str(e)}")


# =========================================================================
# CONTROL DE ASISTENCIA QR Y CIERRE MANUAL DE PLANILLAS
# =========================================================================

@router.post("/verify-qr", response_model=dict)
def verify_user_qr(
    booking_id: int, 
    authorization: str | None = Header(default=None), 
    db: Session = Depends(get_db)
):
    """
    Valida el QR mostrado por el socio en la recepción del club.
    Muta el estado a 'Concreted' e impacta la tabla de asistencias.
    """
    staff_id = _extract_user_id(authorization)
    staff_user = db.query(User).filter(User.id_user == staff_id).first()
    if not staff_user:
        raise HTTPException(status_code=404, detail="Usuario administrativo no encontrado.")

    role_str = str(staff_user.role.value if hasattr(staff_user.role, 'value') else staff_user.role).upper()
    if "ADMIN" not in role_str and "EMPLOYEE" not in role_str and "ADMINISTRATIVE" not in role_str and "EMPLEADO" not in role_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No autorizado: Esta funcionalidad es exclusiva para la administración del club."
        )

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Código inválido: La reserva no existe.")

    status_curr = _booking_status(booking)
    if status_curr == "Concreted":
        raise HTTPException(status_code=400, detail="Acceso denegado: Esta asistencia ya fue registrada.")
    if status_curr == "Cancelled":
        raise HTTPException(status_code=400, detail="Acceso denegado: El socio canceló esta reserva.")
    if status_curr == "Absent":
        raise HTTPException(status_code=400, detail="Acceso denegado: El socio ya figura como Absent.")

    instance = db.query(ShiftInstance).filter(ShiftInstance.id == booking.instance_id).first()
    hoy_local = business_today()
    if not instance or instance.date != hoy_local:
        raise HTTPException(status_code=400, detail=f"Acceso denegado: Esta reserva pertenece al día {instance.date if instance else 'desconocido'}.")

    template = instance.template
    if not template or not template.start_time:
        raise HTTPException(status_code=500, detail="Error de configuración: La clase no tiene un horario asignado.")

    try:
        class_time = datetime.datetime.strptime(template.start_time, "%H:%M").time()
        class_datetime = datetime.datetime.combine(instance.date, class_time)
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno al procesar el horario de la clase.")

    ahora = datetime.datetime.now()
    limite_inferior = class_datetime - datetime.timedelta(minutes=30)
    limite_superior = class_datetime + datetime.timedelta(minutes=30)

    if ahora < limite_inferior:
        raise HTTPException(
            status_code=400, 
            detail=f"Muy temprano. Ingreso permitido desde las {limite_inferior.strftime('%H:%M')} hs."
        )
        
    if ahora > limite_superior:
        booking.status = "Absent"
        user = db.query(User).filter(User.id_user == booking.user_id).first()
        if user and hasattr(user, 'missed_classes_count'):
            user.missed_classes_count = (user.missed_classes_count or 0) + 1
        db.commit()
        raise HTTPException(status_code=400, detail="Tolerancia expirada: El socio quedó registrado como Absent.")

    booking.status = "Concreted"
    
    try:
        from ..models.attendance import Attendance
        nueva_asistencia = Attendance(
            user_id=booking.user_id,
            instance_id=booking.instance_id,
            is_present=True
        )
        db.add(nueva_asistencia)
    except Exception:
        pass

    db.commit()

    return {
        "message": "¡Asistencia Concretada!",
        "booking_id": booking.id,
        "status": booking.status,
        "client_name": f"{booking.user.first_name} {booking.user.last_name}" if booking.user else "Socio",
        "activity_name": template.activity.name if template and template.activity else "Clase"
    }


@router.put("/instances/{instance_id}/close", response_model=dict)
def close_class_instance(
    instance_id: int, 
    authorization: str | None = Header(default=None), 
    db: Session = Depends(get_db)
):
    """
    Cierre de Planilla por el Administrativo (Estrategia Manual).
    Pasa todas las reservas 'Pending' de la clase a 'Absent'.
    """
    staff_id = _extract_user_id(authorization)
    staff_user = db.query(User).filter(User.id_user == staff_id).first()
    if not staff_user:
        raise HTTPException(status_code=404, detail="Usuario administrativo no encontrado.")
        
    role_str = str(staff_user.role.value if hasattr(staff_user.role, 'value') else staff_user.role).upper()
    if "ADMIN" not in role_str and "EMPLOYEE" not in role_str and "ADMINISTRATIVE" not in role_str and "EMPLEADO" not in role_str:
        raise HTTPException(status_code=403, detail="No autorizado para realizar cierres de planillas.")

    instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="La clase especificada no existe.")

    pending_bookings = db.query(Booking).filter(
        Booking.instance_id == instance_id,
        (Booking.status == "Pending") | (Booking.status.is_(None))
    ).all()

    count_absentees = 0
    for booking in pending_bookings:
        booking.status = "Absent"
        count_absentees += 1
        
        user = db.query(User).filter(User.id_user == booking.user_id).first()
        if user and hasattr(user, 'missed_classes_count'):
            user.missed_classes_count = (user.missed_classes_count or 0) + 1

    if count_absentees > 0:
        db.commit()

    return {
        "message": "Planilla de asistencias guardada y cerrada con éxito.",
        "instance_id": instance_id,
        "absentees_processed": count_absentees
    }


# =========================================================================
# ENDPOINTS DE DEBUG DIAGNÓSTICO
# =========================================================================

@router.get("/debug/auth", tags=["debug"])
def debug_auth(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    debug_info = {
        "authorization_header_received": authorization is not None,
        "authorization_header": authorization[:30] + "..." if authorization and len(authorization) > 30 else authorization,
        "extracted_user_id": None,
        "all_bookings_in_db": 0,
        "bookings_for_extracted_user": None,
    }

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        user_id = get_user_id_from_token(token)
        debug_info["extracted_user_id"] = user_id

        if user_id:
            bookings_count = db.query(Booking).filter(Booking.user_id == user_id).count()
            debug_info["bookings_for_extracted_user"] = bookings_count

    total_bookings = db.query(Booking).count()
    debug_info["all_bookings_in_db"] = total_bookings
    return debug_info


@router.get("/debug/all", tags=["debug"])
def debug_all_bookings(db: Session = Depends(get_db)):
    from sqlalchemy import func
    result = db.query(Booking.user_id, func.count(Booking.id).label('count')).group_by(Booking.user_id).all()

    bookings_by_user = {}
    for user_id, count in result:
        bookings_by_user[user_id] = count

    return {
        "total_bookings": db.query(Booking).count(),
        "bookings_by_user_id": bookings_by_user,
    }


@router.get("/debug/user/{user_id}", tags=["debug"])
def debug_user_bookings(user_id: int, db: Session = Depends(get_db)):
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    result = []
    for booking in bookings:
        instance = db.query(ShiftInstance).filter(ShiftInstance.id == booking.instance_id).first()
        activity_name = None
        day_of_week = None
        start_time = None
        booking_date = None

        if instance:
            booking_date = instance.date
            day_of_week = instance.template.day_of_week if instance.template else None
            start_time = instance.template.start_time if instance.template else None
            if instance.template and instance.template.activity:
                activity_name = instance.template.activity.name

        result.append({
            "id": booking.id,
            "user_id": booking.user_id,
            "instance_id": booking.instance_id,
            "status": _booking_status(booking),
            "created_at": booking.created_at,
            "activity_name": activity_name,
            "date": booking_date,
            "day_of_week": day_of_week,
            "start_time": start_time,
        })

    return {
        "user_id": user_id,
        "total_bookings": len(result),
        "bookings": result
    }


@router.get("/debug/user-info/{user_id}", tags=["debug"])
def debug_user_info(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id_user == user_id).first()
    if not user:
        return {"error": f"Usuario {user_id} no encontrado"}

    return {
        "id": user.id_user,
        "email": user.email,
        "role": user.role.value if user.role else None,
    }