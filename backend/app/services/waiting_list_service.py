from sqlalchemy import and_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from ..models.waiting_list import WaitingList
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking

class WaitingListService:

    @staticmethod
    def join_waiting_list(db: Session, user_id: int, instance_id: int) -> WaitingList:
        # 1. Verificar si la clase existe
        instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="La clase especificada no existe."
            )

        booked_count = db.query(Booking).filter(
            Booking.instance_id == instance_id,
            Booking.status != "Cancelled"
        ).count()

        if booked_count < instance.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La clase aún tiene cupos disponibles. Realizá una reserva directa."
            )

        already_booked = db.query(Booking).filter(
            Booking.instance_id == instance_id,
            Booking.user_id == user_id,
            Booking.status != "Cancelled"
        ).first()
        if already_booked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya tenés una reserva activa para esta clase."
            )
        
        already_waiting = db.query(WaitingList).filter(
            WaitingList.instance_id == instance_id,
            WaitingList.user_id == user_id,
            WaitingList.status == "waiting"
        ).first()
        if already_waiting:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya te encontrás en la lista de espera para esta clase."
            )

        current_waiting_count = db.query(WaitingList).filter(
            WaitingList.instance_id == instance_id,
            WaitingList.status == "waiting"
        ).count()

        if current_waiting_count >= 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de espera para esta clase ya alcanzó el límite máximo de 10 personas."
            )

        next_position = current_waiting_count + 1

        # 6. Crear el registro
        new_waiting = WaitingList(
            user_id=user_id,
            instance_id=instance_id,
            position=next_position,
            status="waiting"
        )

        db.add(new_waiting)
        db.commit()
        db.refresh(new_waiting)
        return new_waiting

    @staticmethod
    def process_waiting_list_on_cancellation(db: Session, instance_id: int):
        """
        Busca al primer usuario en la lista de espera para la clase dada,
        le crea la reserva automáticamente y actualiza las posiciones del resto.
        """
        #  Obtener el primero de la fila (posición 1 y estado 'waiting')
        next_in_line = (
            db.query(WaitingList)
            .filter(
                and_(
                    WaitingList.instance_id == instance_id,
                    WaitingList.status == "waiting",
                    WaitingList.position == 1
                )
            )
            .first()
        )

        if not next_in_line:
            return  

        #  Promover al usuario: Cambiar su estado a 'promoted' y sacarlo de la cola (posición 0)
        next_in_line.status = "promoted"
        next_in_line.position = 0

        #  Crear la reserva automática para este usuario promovido
        new_booking = Booking(
            user_id=next_in_line.user_id,
            instance_id=instance_id,
            status="Confirmed",  
            payment_status="paid", 
            amount_paid=0.0
        )
        db.add(new_booking)

        # EFECTO DOMINÓ: Desplazar a todos los demás que siguen esperando en la lista
        remaining_waiting = (
            db.query(WaitingList)
            .filter(
                and_(
                    WaitingList.instance_id == instance_id,
                    WaitingList.status == "waiting"
                )
            )
            .order_by(WaitingList.position.asc())
            .all()
        )

        for idx, entry in enumerate(remaining_waiting):
            entry.position = idx + 1

        db.commit()