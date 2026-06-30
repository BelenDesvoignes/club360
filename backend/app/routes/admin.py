from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import UserRegister, UserResponse
from ..auth_utils import get_password_hash
from ..auth_utils import get_user_id_from_token
from ..services import subscription_service
from ..services.subscription_service import get_subscription_quote
from pydantic import BaseModel
from datetime import datetime, date as date_type
from calendar import monthrange
from ..models.shift_template import ShiftTemplate
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.subscription import Subscription
from ..models.payment import Payment
from ..time_override import business_today, business_utcnow

class AbonoPayload(BaseModel):
    template_id: int


router = APIRouter(prefix="/admin", tags=["admin"])


def _extract_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    return user_id


def _require_admin(authorization: str | None, db: Session) -> User:
    user_id = _extract_user_id(authorization)
    user = db.query(User).filter(User.id_user == user_id).first()
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    return user

@router.post("/crear-equipo", response_model=UserResponse)
def crear_miembro_equipo(user_in: UserRegister, db: Session = Depends(get_db)):

    if db.query(User).filter(User.dni == user_in.dni).first():
        raise HTTPException(
            status_code=400,
            detail="Ya existe un usuario registrado con ese DNI."
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=400,
            detail="Ya existe una cuenta con ese correo electrónico."
        )

    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/crear-cliente", response_model=UserResponse)
def crear_cliente(user_in: UserRegister, db: Session = Depends(get_db)):

    if db.query(User).filter(User.dni == user_in.dni).first():
        raise HTTPException(
            status_code=400,
            detail="Ya existe un usuario registrado con ese DNI."
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=400,
            detail="Ya existe una cuenta con ese correo electrónico."
        )

    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=UserRole.CLIENT
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/clientes")
def listar_clientes(db: Session = Depends(get_db)):

    # Trae todos los usuarios de la base de datos que sean Clientes
    result = db.query(User).filter(User.role == UserRole.CLIENT).all()

    clients_list = []
    for user in result:
        clients_list.append({
            "id": user.id_user,
            "nombre": f"{user.first_name} {user.last_name}",
            "dni": user.dni,
            "estado": "Suspendido" if user.is_suspended else "Activo"
        })
    return clients_list


@router.patch("/clientes/{client_id}/suspension")
def alternar_suspension_cliente(client_id: int, db: Session = Depends(get_db)):

    # Endpoint para suspender o levantar la suspensión usando 'id_user'
    user = db.query(User).filter(User.id_user == client_id, User.role == UserRole.CLIENT).first()
    if not user:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    # Invertimos el valor de tu columna real
    user.is_suspended = not user.is_suspended
    db.commit()

    nuevo_estado = "Suspendido" if user.is_suspended else "Activo"
    return {"message": f"Estado cambiado a {nuevo_estado}", "nuevo_estado": nuevo_estado}



# -------------------------------------------------------
# 1. Listar instancias disponibles para reservar
# -------------------------------------------------------
@router.get("/clientes/{client_id}/instancias-disponibles")
def listar_instancias_disponibles(
    client_id: int,
    activity_id: int | None = None,
    day_of_week: str | None = None,
    db: Session = Depends(get_db)
):
    cliente = db.query(User).filter(User.id_user == client_id, User.role == UserRole.CLIENT).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    query = (
        db.query(ShiftInstance)
        .join(ShiftTemplate, ShiftInstance.template_id == ShiftTemplate.id)
        .filter(
            ShiftInstance.date >= business_today(),
            ShiftInstance.is_cancelled == False,
            ShiftTemplate.is_active == True,
        )
    )

    if activity_id:
        query = query.filter(ShiftTemplate.activity_id == activity_id)
    if day_of_week:
        query = query.filter(ShiftTemplate.day_of_week == day_of_week)

    instances = query.order_by(ShiftInstance.date).all()

    result = []
    for inst in instances:
        # Calcular cupos ocupados
        ocupados = db.query(Booking).filter(
            Booking.instance_id == inst.id,
            Booking.status != "Cancelled"
        ).count()
        disponibles = inst.capacity - ocupados

        # Verificar si el cliente ya tiene reserva o está en lista de espera
        ya_reservado = db.query(Booking).filter(
            Booking.instance_id == inst.id,
            Booking.user_id == client_id,
            Booking.status != "Cancelled"
        ).first()

        if ya_reservado:
            continue

        from ..models.waiting_list import WaitingList
        ya_en_espera = db.query(WaitingList).filter(
            WaitingList.instance_id == inst.id,
            WaitingList.user_id == client_id,
            WaitingList.status == "waiting"
        ).first()

        if ya_en_espera:
            continue

        esta_llena = disponibles <= 0

        result.append({
            "instance_id": inst.id,
            "date": inst.date,
            "day_of_week": inst.template.day_of_week,
            "start_time": inst.template.start_time,
            "activity_id": inst.template.activity_id,
            "activity_name": inst.template.activity.name if inst.template.activity else None,
            "price": inst.template.price,
            "cupos_disponibles": max(disponibles, 0),
            "esta_llena": esta_llena,
        })

    return result


class ReservaParaClientePayload(BaseModel):
    instance_id: int

@router.post("/clientes/{client_id}/reservar-clase")
def reservar_clase_para_cliente(
    client_id: int,
    payload: ReservaParaClientePayload,
    db: Session = Depends(get_db)
):
    from ..services.waiting_list_service import WaitingListService
    from ..models.waiting_list import WaitingList

    cliente = db.query(User).filter(User.id_user == client_id, User.role == UserRole.CLIENT).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    instancia = db.query(ShiftInstance).filter(ShiftInstance.id == payload.instance_id).first()
    if not instancia:
        raise HTTPException(status_code=404, detail="Instancia no encontrada.")

    ya_reservado = db.query(Booking).filter(
        Booking.instance_id == payload.instance_id,
        Booking.user_id == client_id,
        Booking.status != "Cancelled"
    ).first()
    if ya_reservado:
        raise HTTPException(status_code=400, detail="El cliente ya tiene una reserva en este turno.")

    ocupados = db.query(Booking).filter(
        Booking.instance_id == payload.instance_id,
        Booking.status != "Cancelled"
    ).count()

    precio_total = instancia.template.price

    if ocupados >= instancia.capacity:
        # Sin cupo: anotar en lista de espera
        try:
            entry = WaitingListService.join_waiting_list_record(
                db=db,
                user_id=client_id,
                instance_id=payload.instance_id,
                entry_type="single",
            )
            return {
                "resultado": "lista_espera",
                "waiting_list_id": entry.id,
                "position": entry.position,
                "mensaje": f"Sin cupos disponibles. {cliente.first_name} {cliente.last_name} fue anotado/a en la lista de espera (posición {entry.position}).",
            }
        except HTTPException as he:
            raise he
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error al anotar en lista de espera: {str(e)}")

    try:
        booking = Booking(
            user_id=client_id,
            instance_id=payload.instance_id,
            status="Confirmed",
            amount_paid=precio_total,
            payment_status="paid",
        )
        db.add(booking)

        payment = Payment(
            user_id=client_id,
            amount=precio_total,
            status="completed",
            type="booking",
            date=business_utcnow(),
        )
        db.add(payment)

        db.commit()
        db.refresh(booking)

        return {
            "resultado": "confirmado",
            "booking_id": booking.id,
            "status": booking.status,
            "amount_paid": booking.amount_paid,
            "payment_status": booking.payment_status,
            "precio_total": precio_total,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# -------------------------------------------------------
# 3. Marcar pago restante como pagado
# -------------------------------------------------------
@router.patch("/clientes/{client_id}/reservas/{booking_id}/pagar-restante")
def pagar_restante(
    client_id: int,
    booking_id: int,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == client_id,
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    if booking.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Esta reserva ya fue pagada en su totalidad.")

    if booking.status == "Cancelled":
        raise HTTPException(status_code=400, detail="No se puede pagar una reserva cancelada.")

    precio_total = booking.instance.template.price
    restante = round(precio_total - (booking.amount_paid or 0), 2)

    try:
        booking.amount_paid = precio_total
        booking.payment_status = "paid"

        payment = Payment(
            user_id=client_id,
            amount=restante,
            status="completed",
            type="booking",
            date=business_utcnow(),
        )
        db.add(payment)
        db.commit()

        return {
            "booking_id": booking.id,
            "payment_status": booking.payment_status,
            "amount_paid": booking.amount_paid,
            "mensaje": "Pago completado correctamente."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# -------------------------------------------------------
# 5. Listar reservas de un cliente
# -------------------------------------------------------
@router.get("/clientes/{client_id}/reservas")
def listar_reservas_cliente(client_id: int, db: Session = Depends(get_db)):

    cliente = db.query(User).filter(User.id_user == client_id, User.role == UserRole.CLIENT).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == client_id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    result = []
    for b in bookings:
        instance = b.instance
        result.append({
            "booking_id": b.id,
            "status": b.status,
            "payment_status": b.payment_status,
            "amount_paid": b.amount_paid,
            "created_at": b.created_at,
            "activity_name": instance.template.activity.name if instance and instance.template and instance.template.activity else None,
            "date": instance.date if instance else None,
            "day_of_week": instance.template.day_of_week if instance and instance.template else None,
            "start_time": instance.template.start_time if instance and instance.template else None,
            "price": instance.template.price if instance and instance.template else None,
            "is_subscription": b.subscription_id is not None,
        })

    return result

# -------------------------------------------------------
# Registrar abono mensual para un cliente
# -------------------------------------------------------

@router.get("/clientes/{client_id}/abono-quote")
def get_abono_quote_para_cliente(
    client_id: int,
    template_id: int,
    db: Session = Depends(get_db)
):
    cliente = db.query(User).filter(User.id_user == client_id, User.role == UserRole.CLIENT).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    quote = get_subscription_quote(db, user_id=client_id, template_id=template_id)
    return {
        "template_id": quote.template_id,
        "valid_to": str(quote.valid_to),
        "remaining_classes": quote.remaining_classes,
        "base_amount": quote.base_amount,
        "amount": quote.amount,
        "discount_percent": quote.discount_percent,
        "discount_applied": quote.discount_applied,
        "pay_now_required": quote.pay_now_required,
        "discount_reason": quote.discount_reason,
    }


@router.post("/clientes/{client_id}/registrar-abono")
def registrar_abono(
    client_id: int,
    payload: AbonoPayload,
    db: Session = Depends(get_db)
):
    cliente = db.query(User).filter(User.id_user == client_id, User.role == UserRole.CLIENT).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Horario no encontrado.")

    if not template.is_active:
        raise HTTPException(status_code=400, detail="Este horario no está activo.")

    from ..services.waiting_list_service import WaitingListService

    # Precio con las mismas reglas que el flujo del cliente
    quote = get_subscription_quote(db, user_id=client_id, template_id=payload.template_id)
    monto = quote.amount

    hoy = business_utcnow()
    mes_actual = hoy.month
    anio_actual = hoy.year
    ultimo_dia = monthrange(anio_actual, mes_actual)[1]
    valid_to = date_type(anio_actual, mes_actual, ultimo_dia)

    # Verificar que no tenga ya un abono activo para este template en este mes
    abono_existente = db.query(Subscription).filter(
        Subscription.user_id == client_id,
        Subscription.template_id == payload.template_id,
        Subscription.month == mes_actual,
        Subscription.status == "active"
    ).first()
    if abono_existente:
        raise HTTPException(status_code=400, detail="El cliente ya tiene un abono activo para este horario este mes.")

    # Instancias desde hoy hasta fin de mes (igual que el flujo del cliente)
    instancias = db.query(ShiftInstance).filter(
        ShiftInstance.template_id == payload.template_id,
        ShiftInstance.date >= hoy.date(),
        ShiftInstance.date <= valid_to,
        ShiftInstance.is_cancelled == False,
    ).all()

    try:
        subscription = Subscription(
            user_id=client_id,
            template_id=payload.template_id,
            month=mes_actual,
            status="active",
            price_paid=monto,
            purchase_date=hoy,
            valid_to=valid_to,
        )
        db.add(subscription)
        db.flush()

        bookings_creados = 0
        clases_en_espera = 0
        for instancia in instancias:
            ya_reservado = db.query(Booking).filter(
                Booking.instance_id == instancia.id,
                Booking.user_id == client_id,
                Booking.status != "Cancelled"
            ).first()
            if ya_reservado:
                continue

            ocupados = db.query(Booking).filter(
                Booking.instance_id == instancia.id,
                Booking.status != "Cancelled"
            ).count()

            if ocupados >= instancia.capacity:
                # Sin cupo: anotar en lista de espera con prioridad de abono
                WaitingListService.join_waiting_list_record(
                    db=db,
                    user_id=client_id,
                    instance_id=instancia.id,
                    entry_type="subscription",
                    subscription_id=subscription.id,
                    commit=False,
                )
                clases_en_espera += 1
            else:
                booking = Booking(
                    user_id=client_id,
                    instance_id=instancia.id,
                    subscription_id=subscription.id,
                    status="Confirmed",
                    amount_paid=0,
                    payment_status="paid",
                )
                db.add(booking)
                bookings_creados += 1

        # El admin cobra en efectivo: siempre pago completo
        payment = Payment(
            user_id=client_id,
            amount=monto,
            status="completed",
            type="subscription",
            date=hoy,
        )
        db.add(payment)
        db.commit()

        mensaje = f"Abono registrado con éxito. Se reservaron {bookings_creados} clases."
        if clases_en_espera:
            mensaje += f" {clases_en_espera} clase(s) sin cupo fueron anotadas en lista de espera."

        return {
            "subscription_id": subscription.id,
            "template_id": payload.template_id,
            "monto": monto,
            "discount_applied": quote.discount_applied,
            "discount_reason": quote.discount_reason,
            "month": mes_actual,
            "valid_to": valid_to,
            "clases_reservadas": bookings_creados,
            "clases_en_espera": clases_en_espera,
            "mensaje": mensaje,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")



@router.get("/clientes/{client_id}/pagos")
def listar_pagos_cliente(client_id: int, db: Session = Depends(get_db)):
    from ..models.subscription import Subscription
    from ..models.activity import Activity

    cliente = db.query(User).filter(User.id_user == client_id, User.role == UserRole.CLIENT).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    pagos = (
        db.query(Payment)
        .filter(Payment.user_id == client_id)
        .order_by(Payment.date.desc())
        .all()
    )

    # Cargamos subscriptions y bookings una sola vez para correlacionar por fecha
    subscriptions = (
        db.query(Subscription)
        .filter(Subscription.user_id == client_id)
        .all()
    )
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == client_id)
        .all()
    )

    def _activity_for_payment(p: Payment) -> str | None:
        try:
            if not p.date:
                return None
            p_dt = p.date.replace(tzinfo=None) if hasattr(p.date, 'tzinfo') and p.date.tzinfo else p.date
            if p.type == "subscription":
                closest = min(
                    (s for s in subscriptions if s.purchase_date),
                    key=lambda s: abs(((s.purchase_date.replace(tzinfo=None) if s.purchase_date.tzinfo else s.purchase_date) - p_dt).total_seconds()),
                    default=None,
                )
                if closest:
                    try:
                        return closest.template.activity.name
                    except Exception:
                        pass
            elif p.type == "booking":
                closest = min(
                    (b for b in bookings if b.created_at),
                    key=lambda b: abs(((b.created_at.replace(tzinfo=None) if b.created_at.tzinfo else b.created_at) - p_dt).total_seconds()),
                    default=None,
                )
                if closest:
                    try:
                        return closest.instance.template.activity.name
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    return [
        {
            "payment_id": p.id,
            "amount": p.amount,
            "status": p.status,
            "type": p.type,
            "date": p.date,
            "activity_name": _activity_for_payment(p),
        }
        for p in pagos
    ]