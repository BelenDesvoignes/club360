from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.attendance import Attendance
from ..models.shift_instance import ShiftInstance
from ..auth_utils import get_user_id_from_token
from datetime import date

from ..time_override import business_today

router = APIRouter(prefix="/attendances", tags=["attendances"])


def _extract_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return user_id


@router.get("/my-month-count")
def get_my_month_attendance_count(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_id(authorization)

    hoy = business_today()
    primer_dia = hoy.replace(day=1)

    asistencias = (
        db.query(Attendance)
        .join(ShiftInstance, Attendance.instance_id == ShiftInstance.id)
        .filter(
            Attendance.user_id == user_id,
            Attendance.is_present == True,
            ShiftInstance.date >= primer_dia,
            ShiftInstance.date <= hoy,
        )
        .count()
    )

    return {"count": asistencias}