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

router = APIRouter(prefix="/bookings", tags=["bookings"])


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
    booking = booking_service.create_booking(db, user_id, data.instance_id)
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
            "status": booking.status,
            "created_at": booking.created_at,
            "activity_name": activity_name,
            "date": booking_date,
            "day_of_week": day_of_week,
            "start_time": start_time,
        })

    return result


@router.get("/me", response_model=list[BookingListOut])
def get_my_bookings(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user_id = _extract_user_id(authorization)
    return get_user_bookings(user_id, db)


@router.get("/debug/auth", tags=["debug"])
def debug_auth(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Endpoint de debug para diagnosticar autenticación"""
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
    
    # Total de bookings en toda la BD
    total_bookings = db.query(Booking).count()
    debug_info["all_bookings_in_db"] = total_bookings
    
    return debug_info


@router.get("/debug/all", tags=["debug"])
def debug_all_bookings(db: Session = Depends(get_db)):
    """Endpoint de debug para ver TODOS los bookings por user_id"""
    from sqlalchemy import func
    
    # Agrupar bookings por user_id y contar
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
    """Endpoint de debug para ver los bookings de un user_id específico"""
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
            "status": booking.status,
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
    """Endpoint de debug para ver info del usuario"""
    from ..models.user import User
    
    user = db.query(User).filter(User.id_user == user_id).first()
    
    if not user:
        return {"error": f"Usuario {user_id} no encontrado"}
    
    return {
        "id": user.id_user,
        "email": user.email,
        "role": user.role.value if user.role else None,
    }


@router.post("/{booking_id}/cancel", response_model=dict)
def cancel_booking(booking_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    from app.models.user import UserRole
    
    user_id = _extract_user_id(authorization)

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    # Solo puede cancelar el dueño de la reserva o un admin
    requester = db.query(User).filter(User.id_user == user_id).first()
    if booking.user_id != user_id and (not requester or requester.role != UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="No autorizado para cancelar esta reserva")

    booking.status = 'Cancelled'
    db.commit()

    return {"message": "Reserva cancelada exitosamente"}
