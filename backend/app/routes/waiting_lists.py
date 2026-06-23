from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..services.waiting_list_service import WaitingListService
from ..schemas.waiting_list_schema import WaitingListResponse
from ..auth_utils import get_user_id_from_token, get_current_user_role
from fastapi import Response, HTTPException
from ..schemas.bookings import BookingListOut

router = APIRouter(
    prefix="/waiting-lists",
    tags=["Waiting Lists"]
)

@router.get("/instance/{instance_id}", response_model=List[WaitingListResponse])
def get_instance_waiting_list(
    instance_id: int,
    db: Session = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """
    Retorna la lista de personas en espera para una clase específica. 
    Solo accesible por admin/empleado.
    """
    if role not in ["admin", "empleado"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver esta lista")
        
    return WaitingListService.get_waiting_list_by_instance(db, instance_id)

@router.post("/join", response_model=WaitingListResponse, status_code=status.HTTP_201_CREATED)
async def join_class_waiting_list( 
    instance_id: int, 
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id_from_token)  
):
    """
    Permite a un cliente autenticado anotarse en la lista de espera 
    de una clase cuyo cupo esté totalmente completo.
    """
    new_entry = await WaitingListService.join_waiting_list(
        db=db, 
        user_id=user_id, 
        instance_id=instance_id
    )
    return new_entry


@router.get("/me", response_model=List[WaitingListResponse])
def my_waiting_lists(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id_from_token),
):
    return WaitingListService.get_user_waiting_entries(db, user_id)


@router.delete("/{waiting_id}", status_code=status.HTTP_204_NO_CONTENT)
def leave_waiting_list(
    waiting_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id_from_token),
):
    WaitingListService.leave_waiting_list(db, user_id, waiting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/offer/{token}", status_code=status.HTTP_200_OK)
def get_promotion_offer(
    token: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id_from_token)
):
    """
    Devuelve el detalle de la oferta para mostrar aceptar/rechazar dentro de la app.
    El token viene del link del email, no requiere autenticación.
    """
    return WaitingListService.get_promotion_offer(db, token, authenticated_user_id=user_id)


@router.post("/accept/{accept_token}", response_model=BookingListOut, status_code=status.HTTP_201_CREATED)
def accept_promotion(
    accept_token: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id_from_token)
):
    """
    Acepta la promoción desde la lista de espera.
    El token viene del link del email y la aceptación requiere la cuenta del socio.
    """
    from ..models.shift_instance import ShiftInstance
    
    booking = WaitingListService.accept_promotion(db, accept_token, authenticated_user_id=user_id)
    
    # Enriquecer booking con datos de la instancia
    instance = db.query(ShiftInstance).filter(ShiftInstance.id == booking.instance_id).first()
    if instance and instance.template:
        booking.activity_name = instance.template.activity.name if instance.template.activity else None
        booking.date = instance.date
        booking.start_time = instance.template.start_time
        booking.price = instance.template.price
        if instance.date:
            try:
                booking.day_of_week = instance.date.strftime('%A')
            except:
                booking.day_of_week = None
    
    return booking


@router.post("/reject/{reject_token}", status_code=status.HTTP_200_OK)
async def reject_promotion(
    reject_token: str,
    db: Session = Depends(get_db)
):
    """
    Rechaza la promoción desde la lista de espera.
    Continúa con el siguiente en la fila.
    El token viene del link del email, no requiere autenticación.
    """
    await WaitingListService.reject_promotion(db, reject_token)
    return {"message": "Inscripción rechazada. Continuamos con el siguiente en la lista."}
