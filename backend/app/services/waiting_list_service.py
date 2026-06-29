from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from ..models.waiting_list import WaitingList
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.user import User
from typing import List
from datetime import datetime, timedelta
from ..time_override import business_utcnow
from ..models.user import User, UserRole
from ..mail import send_admin_waitlist_alert
import secrets
import os

class WaitingListService:
    @staticmethod
    def get_promotion_offer(db: Session, token: str, authenticated_user_id: int | None = None) -> dict:
        entry = (
            db.query(WaitingList)
            .options(joinedload(WaitingList.instance).joinedload(ShiftInstance.template))
            .filter(WaitingList.promotion_token == token)
            .first()
        )

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token inválido o expirado."
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

        instance = entry.instance
        template = instance.template if instance else None
        activity = template.activity if template and template.activity else None

        return {
            "id": entry.id,
            "instance_id": entry.instance_id,
            "activity_name": activity.name if activity else "Actividad",
            "date": instance.date if instance else None,
            "start_time": template.start_time if template else None,
            "price": float(template.price or 0) if template else 0.0,
            "expires_at": entry.promotion_expires_at,
            "owner_mismatch": authenticated_user_id is not None and authenticated_user_id != entry.user_id,
        }

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
    async def join_waiting_list(db: Session, user_id: int, instance_id: int, entry_type: str = "single", subscription_id: int | None = None) -> WaitingList:
        instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="La clase no existe."
            )

        booked_count = db.query(Booking).filter(
            Booking.instance_id == instance_id,
            Booking.status != "Cancelled"
        ).count()

        now = business_utcnow()
        has_active_queue = db.query(WaitingList).filter(
            WaitingList.instance_id == instance_id,
            or_(
                WaitingList.status == "waiting",
                and_(
                    WaitingList.status == "notified",
                    or_(
                        WaitingList.promotion_expires_at == None,
                        WaitingList.promotion_expires_at >= now,
                    ),
                ),
            )
        ).first() is not None

        if booked_count < instance.capacity and not has_active_queue:
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
                detail="Ya estás en la lista de espera para esta clase."
            )

        current_waiting_count = db.query(WaitingList).filter(
            WaitingList.instance_id == instance_id,
            WaitingList.status == "waiting"
        ).count()


        new_total_count = current_waiting_count + 1

        if new_total_count == 10:
            admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
            
            if admins and instance:
                actividad = instance.template.activity.name if instance.template and instance.template.activity else 'Actividad'
                fecha = instance.date.strftime("%d/%m/%Y") if instance.date else "Sin fecha"
                hora = instance.template.start_time if instance.template and instance.template.start_time else "Sin hora"
                
                for admin in admins:
                    try:
                        await send_admin_waitlist_alert(
                            admin_email=admin.email,
                            instance_id=instance_id,
                            count=new_total_count,
                            actividad=actividad,
                            fecha=fecha,
                            hora=hora
                        )
                    except Exception as e:
                        print(f"Error enviando alerta de lista al admin {admin.email}: {e}", flush=True)

        next_position = current_waiting_count + 1

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

        promotion_token = secrets.token_urlsafe(32)
        
        now = business_utcnow()
        expires_at = now + timedelta(hours=24)

        original_position = next_in_line.position
        next_in_line.status = "notified"
        next_in_line.promotion_token = promotion_token
        next_in_line.promotion_expires_at = expires_at
        next_in_line.promoted_at = now
        next_in_line.position = 0 

        user = db.query(User).filter(User.id_user == next_in_line.user_id).first()
        instance = db.query(ShiftInstance).filter(ShiftInstance.id == instance_id).first()
        
        db.commit()

        if user and instance:
            nombre = f"{user.first_name} {user.last_name}".strip() if hasattr(user, 'first_name') else user.email
            actividad = instance.template.activity.name if instance.template and instance.template.activity else 'Actividad'
            fecha = instance.date.strftime("%d/%m/%Y") if instance.date else "Sin fecha"
            hora = instance.template.start_time if instance.template and instance.template.start_time else "Sin hora"
            
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
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
                next_in_line.status = "waiting"
                next_in_line.promotion_token = None
                next_in_line.promotion_expires_at = None
                next_in_line.promoted_at = None
                next_in_line.position = original_position
                db.commit()
                print(f"Error enviando email de promoción: {e}", flush=True)
                raise

    @staticmethod
    def accept_promotion(db: Session, accept_token: str, authenticated_user_id: int | None = None) -> Booking:
        """
        Acepta la promoción de la lista de espera y crea la Booking.
        Retorna la Booking creada.
        """
        entry = db.query(WaitingList).filter(WaitingList.promotion_token == accept_token).first()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token inválido o expirado."
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

        if authenticated_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Iniciá sesión para aceptar y pagar este cupo."
            )

        if entry.user_id != authenticated_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este cupo pertenece a otro socio. Iniciá sesión con la cuenta anotada en la lista de espera."
            )

        new_booking = Booking(
            user_id=entry.user_id,
            instance_id=entry.instance_id,
            status="Pending",
            payment_status="partial",
            amount_paid=0.0,
            subscription_id=entry.subscription_id,
            created_at=now  
        )
        db.add(new_booking)

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

        entry.status = "rejected"
        entry.promotion_token = None
        entry.promotion_expires_at = None

        db.commit()

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
            return

        entry.status = "cancelled"

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
