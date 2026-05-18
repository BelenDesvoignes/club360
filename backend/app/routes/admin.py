from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import UserRegister, UserResponse
from ..auth_utils import get_password_hash
from ..auth_utils import get_user_id_from_token
from app.services import subscription_service
# Asumo que tienes una función para obtener el usuario actual desde el token
# from app.routes.auth import get_current_admin_user

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