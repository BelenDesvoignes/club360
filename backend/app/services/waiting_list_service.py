from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from ..models.waiting_list import WaitingList
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.user import User
from typing import List
from datetime import datetime, timedelta
from ..time_override import business_utcnow
import secrets
import os

class WaitingListService:

    @staticmethod
    def get_waiting_list_by_instance(db: Session, instance_id: int) -> List[WaitingList]:
        return (
            db.query(WaitingList)
            .options(joinedload(WaitingList.user))
            .filter(
                WaitingList.instance_id == instance_id,
                WaitingList.status == "waiting"
            )
            .order_by(WaitingList.position.asc())
            .all()
        )

    @staticmethod
    def join_waiting_list(db: Session, user_id: int, instance_id: int, entry_type: str = "single", subscription_id: int | None = None) -> WaitingList:
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
            status="waiting",
            entry_type=entry_type,
            subscription_id=subscription_id,
        )

        db.add(new_waiting)
        db.commit()
        db.refresh(new_waiting)
        return new_waiting

    @staticmethod
    async def process_waiting_list_on_cancellation(db: Session, instance_id: int, prefer_subscription: bool = False):
        """
        Procesa la lista de espera cuando se libera un cupo en `instance_id`.

        Comportamiento:
        - Genera un token único y establece expiración de 24 horas
        - Marca el entry promovido como "notified" (no "promoted")
        - Envía email con links de aceptar/rechazar (ambos usan el mismo token)
        - La Booking solo se crea cuando el usuario hace click en "Aceptar"
        
        Si `prefer_subscription` es True, se prioriza el primer registro con 
        `entry_type == 'subscription'`. Si no existe, se promociona el primero general.
        """
        from ..mail import send_waitlist_promotion_offer
        
        # Intentar obtener el siguiente en la fila según la preferencia
        next_in_line = None

        if prefer_subscription:
            next_in_line = (
                db.query(WaitingList)
                .filter(
                    and_(
                        WaitingList.instance_id == instance_id,
                        WaitingList.status == "waiting",
                        WaitingList.entry_type == "subscription",
                    )
                )
                .order_by(WaitingList.position.asc())
                .first()
            )

        # Si no encontramos con preferencia (o no se pidió), tomar el primer general
        if not next_in_line:
            next_in_line = (
                db.query(WaitingList)
                .filter(
                    and_(
                        WaitingList.instance_id == instance_id,
                        WaitingList.status == "waiting",
                    )
                )
                .order_by(WaitingList.position.asc())
                .first()
            )

        if not next_in_line:
            return

        # Generar token único para aceptar/rechazar
        promotion_token = secrets.token_urlsafe(32)
        
        now = business_utcnow()
        expires_at = now + timedelta(hours=24)

        # Marcar como notificado (no promovido aún)
        original_position = next_in_line.position
        next_in_line.status = "notified"
        next_in_line.promotion_token = promotion_token
        next_in_line.promotion_expires_at = expires_at
        next_in_line.promoted_at = now
        next_in_line.position = 0  # Sacarlo de la fila mientras espera respuesta

        # Obtener datos del usuario y la clase
        user = db.query(User).filter(User.id_user == next_in_line.user_id).first()
        instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
        
        db.commit()

        # Enviar email con los links (fuera de la transacción para que se vea el estado actualizado)
        if user and instance:
            nombre = f"{user.first_name} {user.last_name}".strip() if hasattr(user, 'first_name') else user.email
            actividad = instance.template.activity.name if instance.template and instance.template.activity else 'Actividad'
            fecha = instance.date.strftime("%d/%m/%Y") if instance.date else "Sin fecha"
            hora = instance.template.start_time if instance.template and instance.template.start_time else "Sin hora"
            
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5174")
            try:
                await send_waitlist_promotion_offer(
                    email=user.email,
                    nombre=nombre,
                    actividad=actividad,
                    fecha=fecha,
                    hora=hora,
                    token=promotion_token,
                    frontend_url=frontend_url
                )
            except Exception as e:
                # Si falla el envío, revertimos el estado para no dejarlo como notificado sin mail
                next_in_line.status = "waiting"
                next_in_line.promotion_token = None
                next_in_line.promotion_expires_at = None
                next_in_line.promoted_at = None
                next_in_line.position = original_position
                db.commit()
                print(f"Error enviando email de promoción: {e}", flush=True)
                raise

    @staticmethod
    def accept_promotion(db: Session, accept_token: str) -> Booking:
        """
        Acepta la promoción de la lista de espera y crea la Booking.
        Retorna la Booking creada.
        """
        entry = db.query(WaitingList).filter(WaitingList.promotion_token == accept_token).first()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token de promoción inválido o expirado."
            )

        now = business_utcnow()
        if entry.promotion_expires_at and now > entry.promotion_expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La oferta de promoción expiró. El cupo fue asignado al siguiente en la fila."
            )

        if entry.status != "notified":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta entrada ya fue procesada."
            )

        # Crear la Booking
        new_booking = Booking(
            user_id=entry.user_id,
            instance_id=entry.instance_id,
            status="Confirmed",
            payment_status="paid",
            amount_paid=0.0,
            subscription_id=entry.subscription_id,
        )
        db.add(new_booking)

        # Marcar como promovido
        entry.status = "promoted"
        entry.promotion_token = None
        entry.promotion_expires_at = None

        db.commit()
        db.refresh(new_booking)
        return new_booking

    @staticmethod
    async def reject_promotion(db: Session, reject_token: str):
        """
        Rechaza la promoción y continúa con el siguiente en la fila.
        """
        # Buscar la entrada por el reject_token
        # (almacenamos accept_token, así que buscamos por entry con ese token y luego rechazamos)
        entry = db.query(WaitingList).filter(WaitingList.promotion_token == reject_token).first()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token de rechazo inválido."
            )

        if entry.status != "notified":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta entrada ya fue procesada."
            )

        # Marcar como rechazada
        entry.status = "rejected"
        entry.promotion_token = None
        entry.promotion_expires_at = None

        db.commit()

        # Procesar el siguiente en la fila
        # (sin preferencia, ya que se rechazó este)
        await WaitingListService.process_waiting_list_on_cancellation(
            db, 
            entry.instance_id, 
            prefer_subscription=False
        )

    @staticmethod
    def get_user_waiting_entries(db: Session, user_id: int) -> List[WaitingList]:
        return (
            db.query(WaitingList)
            .options(joinedload(WaitingList.instance))
            .filter(WaitingList.user_id == user_id)
            .order_by(WaitingList.created_at.desc())
            .all()
        )

    @staticmethod
    def leave_waiting_list(db: Session, user_id: int, waiting_id: int) -> None:
        entry = db.query(WaitingList).filter(WaitingList.id == waiting_id).first()
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrada no encontrada.")

        if entry.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No podés cancelar esta entrada.")

        if entry.status != "waiting":
            # Ya fue procesada o cancelada
            return

        # Marcar como cancelada
        entry.status = "cancelled"

        # Recalcular posiciones para los que quedan
        remaining = (
            db.query(WaitingList)
            .filter(
                WaitingList.instance_id == entry.instance_id,
                WaitingList.status == "waiting"
            )
            .order_by(WaitingList.position.asc())
            .all()
        )

        for idx, e in enumerate(remaining):
            e.position = idx + 1

        db.commit()