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
    # NOTA: Aquí deberías agregar la lógica de seguridad para que solo un admin logueado pase.
    # Por ahora, hagamos la lógica de creación:

    # 1. Verificar si ya existe
    user_exists = db.query(User).filter(
        (User.email == user_in.email) | (User.dni == user_in.dni)
    ).first()

    if user_exists:
        raise HTTPException(
            status_code=400,
            detail="El usuario con este Email o DNI ya existe."
        )

    # 2. Crear instancia (Aquí permitimos definir el ROL que venga del front)
    # Importante: En el frontend enviaremos 'admin' o 'employee'
    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        dni=user_in.dni,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role # Aquí usamos el rol que mandes desde el formulario
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/run-subscription-suspensions")
def run_subscription_suspensions(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Run unpaid-subscription suspension sweep.

    Intended to be called by a scheduled job (cron) starting on day 11.
    """
    _require_admin(authorization, db)
    return subscription_service.suspend_users_for_unpaid_subscriptions(db)