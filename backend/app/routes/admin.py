# ruff: noqa
# pyright: reportGeneralTypeIssues=false, reportAssignmentType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportOperatorIssue=false, reportRedeclaration=false

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import UserRegister, UserResponse
from ..auth_utils import get_password_hash
from ..auth_utils import get_user_id_from_token
from ..services import subscription_service
from pydantic import BaseModel
from datetime import date
from ..models.shift_template import ShiftTemplate
from ..models.shift_instance import ShiftInstance
from ..models.booking import Booking
from ..models.subscription import Subscription
from ..models.payment import Payment
from datetime import datetime
from ..time_override import business_today, business_utcnow


class AbonoPayload(BaseModel):
    template_id: int
    tipo: str  # "completo" o "mitad"


from datetime import datetime, date as date_type
from calendar import monthrange


class AbonoPayload(BaseModel):
    template_id: int
    tipo: str  # "completo" o "mitad"


router = APIRouter(prefix="/admin", tags=["admin"])


def _extract_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado"
        )

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )

    return user_id


def _require_admin(authorization: str | None, db: Session) -> User:
    user_id = _extract_user_id(authorization)
    user = db.query(User).filter(User.id_user == user_id).first()
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado"
        )
    return user


@router.post("/crear-equipo", response_model=UserResponse)
def crear_miembro_equipo(user_in: UserRegister, db: Session = Depends(get_db)):

    if db.query(User).filter(User.dni == user_in.dni).first():
        raise HTTPException(
            status_code=400, detail="Ya existe un usuario registrado con ese DNI."
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=400, detail="Ya existe una cuenta con ese correo electrónico."
        )

    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
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
            status_code=400, detail="Ya existe un usuario registrado con ese DNI."
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=400, detail="Ya existe una cuenta con ese correo electrónico."
        )

    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=UserRole.CLIENT,
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
        clients_list.append(
            {
                "id": user.id_user,
                "nombre": f"{user.first_name} {user.last_name}",
                "dni": user.dni,
                "estado": "Suspendido" if user.is_suspended else "Activo",
            }
        )
    return clients_list


@router.patch("/clientes/{client_id}/suspension")
def alternar_suspension_cliente(client_id: int, db: Session = Depends(get_db)):

    # Endpoint para suspender o levantar la suspensión usando 'id_user'
    user = (
        db.query(User)
        .filter(User.id_user == client_id, User.role == UserRole.CLIENT)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    # Invertimos el valor de tu columna real
    user.is_suspended = not user.is_suspended
    db.commit()

    nuevo_estado = "Suspendido" if user.is_suspended else "Activo"
    return {
        "message": f"Estado cambiado a {nuevo_estado}",
        "nuevo_estado": nuevo_estado,
    }


# -------------------------------------------------------
# 1. Listar instancias disponibles para reservar
# -------------------------------------------------------
@router.get("/clientes/{client_id}/instancias-disponibles")
def listar_instancias_disponibles(
    client_id: int,
    activity_id: int | None = None,
    day_of_week: str | None = None,
    db: Session = Depends(get_db),
):
    cliente = (
        db.query(User)
        .filter(User.id_user == client_id, User.role == UserRole.CLIENT)
        .first()
    )
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
        ocupados = (
            db.query(Booking)
            .filter(Booking.instance_id == inst.id, Booking.status != "Cancelled")
            .count()
        )
        disponibles = inst.capacity - ocupados

        if disponibles <= 0:
            continue

        # Verificar si el cliente ya tiene reserva en esta instancia
        ya_reservado = (
            db.query(Booking)
            .filter(
                Booking.instance_id == inst.id,
                Booking.user_id == client_id,
                Booking.status != "Cancelled",
            )
            .first()
        )

        if ya_reservado:
            continue

        result.append(
            {
                "instance_id": inst.id,
                "date": inst.date,
                "day_of_week": inst.template.day_of_week,
                "start_time": inst.template.start_time,
                "activity_id": inst.template.activity_id,
                "activity_name": inst.template.activity.name
                if inst.template.activity
                else None,
                "price": inst.template.price,
                "cupos_disponibles": disponibles,
            }
        )

    return result


class ReservaParaClientePayload(BaseModel):
    instance_id: int
    amount_paid: float  # 50% o 100% del precio


@router.post("/clientes/{client_id}/reservar-clase")
def reservar_clase_para_cliente(
    client_id: int, payload: ReservaParaClientePayload, db: Session = Depends(get_db)
):
    cliente = (
        db.query(User)
        .filter(User.id_user == client_id, User.role == UserRole.CLIENT)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    instancia = (
        db.query(ShiftInstance).filter(ShiftInstance.id == payload.instance_id).first()
    )
    if not instancia:
        raise HTTPException(status_code=404, detail="Instancia no encontrada.")

    ocupados = (
        db.query(Booking)
        .filter(
            Booking.instance_id == payload.instance_id, Booking.status != "Cancelled"
        )
        .count()
    )
    if ocupados >= instancia.capacity:
        raise HTTPException(status_code=400, detail="No hay cupos disponibles.")

    ya_reservado = (
        db.query(Booking)
        .filter(
            Booking.instance_id == payload.instance_id,
            Booking.user_id == client_id,
            Booking.status != "Cancelled",
        )
        .first()
    )
    if ya_reservado:
        raise HTTPException(
            status_code=400, detail="El cliente ya tiene una reserva en este turno."
        )

    precio_total = instancia.template.price
    minimo = round(precio_total * 0.5, 2)
    if payload.amount_paid < minimo:
        raise HTTPException(
            status_code=400,
            detail=f"El monto mínimo para reservar es ${minimo} (50% del precio).",
        )

    payment_status = "paid" if payload.amount_paid >= precio_total else "partial"

    try:
        booking = Booking(
            user_id=client_id,
            instance_id=payload.instance_id,
            status="Confirmed",
            amount_paid=payload.amount_paid,
            payment_status=payment_status,
        )
        db.add(booking)

        payment = Payment(
            user_id=client_id,
            amount=payload.amount_paid,
            status=payment_status,
            type="booking",
            date=business_utcnow(),
        )
        db.add(payment)

        db.commit()
        db.refresh(booking)

        return {
            "booking_id": booking.id,
            "status": booking.status,
            "amount_paid": booking.amount_paid,
            "payment_status": booking.payment_status,
            "precio_total": precio_total,
            "saldo_pendiente": round(precio_total - booking.amount_paid, 2),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# -------------------------------------------------------
# 3. Marcar pago restante como pagado
# -------------------------------------------------------
@router.patch("/clientes/{client_id}/reservas/{booking_id}/pagar-restante")
def pagar_restante(client_id: int, booking_id: int, db: Session = Depends(get_db)):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.user_id == client_id,
        )
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    if booking.payment_status == "paid":
        raise HTTPException(
            status_code=400, detail="Esta reserva ya fue pagada en su totalidad."
        )

    if booking.status == "Cancelled":
        raise HTTPException(
            status_code=400, detail="No se puede pagar una reserva cancelada."
        )

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
            "mensaje": "Pago completado correctamente.",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# -------------------------------------------------------
# 5. Listar reservas de un cliente
# -------------------------------------------------------
@router.get("/clientes/{client_id}/reservas")
def listar_reservas_cliente(client_id: int, db: Session = Depends(get_db)):

    cliente = (
        db.query(User)
        .filter(User.id_user == client_id, User.role == UserRole.CLIENT)
        .first()
    )
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
        result.append(
            {
                "booking_id": b.id,
                "status": b.status,
                "payment_status": b.payment_status,
                "amount_paid": b.amount_paid,
                "created_at": b.created_at,
                "activity_name": instance.template.activity.name
                if instance and instance.template and instance.template.activity
                else None,
                "date": instance.date if instance else None,
                "day_of_week": instance.template.day_of_week
                if instance and instance.template
                else None,
                "start_time": instance.template.start_time
                if instance and instance.template
                else None,
                "price": instance.template.price
                if instance and instance.template
                else None,
                "is_subscription": b.subscription_id is not None,
            }
        )

    return result


# -------------------------------------------------------
# Registrar abono mensual para un cliente
# -------------------------------------------------------


@router.post("/clientes/{client_id}/registrar-abono")
def registrar_abono(
    client_id: int, payload: AbonoPayload, db: Session = Depends(get_db)
):
    cliente = (
        db.query(User)
        .filter(User.id_user == client_id, User.role == UserRole.CLIENT)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    template = (
        db.query(ShiftTemplate).filter(ShiftTemplate.id == payload.template_id).first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Horario no encontrado.")

    if not template.is_active:
        raise HTTPException(status_code=400, detail="Este horario no está activo.")

    hoy = business_utcnow()
    mes_actual = hoy.month
    anio_actual = hoy.year
    ultimo_dia = monthrange(anio_actual, mes_actual)[1]
    valid_to = date_type(anio_actual, mes_actual, ultimo_dia)

    # Calcular precio
    base = template.price * 4
    monto = round(base * 0.8, 2) if payload.tipo == "mitad" else round(base, 2)

    # Verificar que no tenga ya un abono activo para este template en este mes
    abono_existente = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == client_id,
            Subscription.template_id == payload.template_id,
            Subscription.month == mes_actual,
            Subscription.status == "active",
        )
        .first()
    )
    if abono_existente:
        raise HTTPException(
            status_code=400,
            detail="El cliente ya tiene un abono activo para este horario este mes.",
        )

    # Buscar todas las instancias del mes para este template
    instancias_del_mes = (
        db.query(ShiftInstance)
        .filter(
            ShiftInstance.template_id == payload.template_id,
            ShiftInstance.date >= date_type(anio_actual, mes_actual, 1),
            ShiftInstance.date <= valid_to,
            ShiftInstance.is_cancelled == False,
        )
        .all()
    )

    # Si es "mitad", tomar solo las instancias desde hoy en adelante
    if payload.tipo == "mitad":
        instancias_del_mes = [i for i in instancias_del_mes if i.date >= hoy.date()]

    try:
        # Crear la suscripción
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
        db.flush()  # necesitamos el ID para los bookings

        # Crear un booking por cada instancia del mes
        bookings_creados = 0
        for instancia in instancias_del_mes:
            # Verificar que no tenga ya una reserva en esa instancia
            ya_reservado = (
                db.query(Booking)
                .filter(
                    Booking.instance_id == instancia.id,
                    Booking.user_id == client_id,
                    Booking.status != "Cancelled",
                )
                .first()
            )
            if ya_reservado:
                continue

            # Verificar cupos
            ocupados = (
                db.query(Booking)
                .filter(
                    Booking.instance_id == instancia.id, Booking.status != "Cancelled"
                )
                .count()
            )
            if ocupados >= instancia.capacity:
                continue

            booking = Booking(
                user_id=client_id,
                instance_id=instancia.id,
                subscription_id=subscription.id,
                status="Confirmed",
                amount_paid=0,
                payment_status="paid",  # el abono ya cubre la clase
            )
            db.add(booking)
            bookings_creados += 1

        # Registrar el pago del abono
        payment = Payment(
            user_id=client_id,
            amount=monto,
            status="completed",
            type="subscription",
            activity_id=template.activity_id,
            date=hoy,
        )
        db.add(payment)
        db.commit()

        return {
            "subscription_id": subscription.id,
            "template_id": payload.template_id,
            "tipo": payload.tipo,
            "monto": monto,
            "month": mes_actual,
            "valid_to": valid_to,
            "clases_reservadas": bookings_creados,
            "mensaje": f"Abono registrado con éxito. Se reservaron {bookings_creados} clases.",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/clientes/{client_id}/pagos")
def listar_pagos_cliente(client_id: int, db: Session = Depends(get_db)):
    cliente = (
        db.query(User)
        .filter(User.id_user == client_id, User.role == UserRole.CLIENT)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    pagos = (
        db.query(Payment)
        .filter(Payment.user_id == client_id)
        .order_by(Payment.date.desc())
        .all()
    )

    return [
        {
            "payment_id": p.id,
            "amount": p.amount,
            "status": p.status,
            "type": p.type,
            "date": p.date,
        }
        for p in pagos
    ]
