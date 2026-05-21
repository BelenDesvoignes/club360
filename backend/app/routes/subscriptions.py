from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_utils import get_user_id_from_token
from app.database import get_db
from app.services import subscription_service
from app.services.booking_service import get_active_subscription
from app.services.booking_service import is_user_suspended

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _extract_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    return user_id


@router.get("/me/active")
def get_my_active_subscription(
    template_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_id(authorization)
    subscription = get_active_subscription(db, user_id, template_id, for_date=date.today())

    return {
        "active": subscription is not None,
        "subscription_id": subscription.id if subscription else None,
        "valid_to": str(subscription.valid_to) if subscription and subscription.valid_to else None,
    }


@router.get("/me/status")
def get_my_subscription_status(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_id(authorization)
    # Lazy suspension (TP-friendly): apply rule when user interacts with the system
    subscription_service.ensure_user_suspension_if_unpaid(db, user_id=user_id)
    return {"suspended": is_user_suspended(db, user_id)}


@router.post("/purchase")
def purchase_subscription(
    payload: dict,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user_id = _extract_user_id(authorization)

    template_id = payload.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id es requerido")

    result = subscription_service.purchase_subscription_and_reserve(
        db,
        user_id=user_id,
        template_id=int(template_id),
    )

    return {
        "subscription_id": result.subscription_id,
        "valid_to": str(result.valid_to),
        "price_paid": result.price_paid,
        "instances_created": result.instances_created,
        "bookings_created": result.bookings_created,
        "skipped_full": result.skipped_full,
        "skipped_existing": result.skipped_existing,
    }

@router.get("/my-active")
def get_my_active_subscription_dashboard(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    from app.models.subscription import Subscription
    from app.models.shift_template import ShiftTemplate
    from app.models.activity import Activity
    from datetime import date

    user_id = _extract_user_id(authorization)

    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.valid_to >= date.today(),
        )
        .order_by(Subscription.valid_to.desc())
        .first()
    )

    if not sub:
        return None

    template = db.query(ShiftTemplate).filter(ShiftTemplate.id == sub.template_id).first()
    actividad = db.query(Activity).filter(Activity.id == template.activity_id).first() if template else None

    return {
        "subscription_id": sub.id,
        "actividad": actividad.name if actividad else None,
        "valid_to": str(sub.valid_to),
        "status": sub.status,
    }

@router.get("/my-active-all")
def get_all_my_active_subscriptions(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    from app.models.subscription import Subscription
    from app.models.shift_template import ShiftTemplate
    from app.models.activity import Activity
    from datetime import date

    user_id = _extract_user_id(authorization)

    subs = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.valid_to >= date.today(),
        )
        .order_by(Subscription.valid_to.asc())
        .all()
    )

    result = []
    for sub in subs:
        template = db.query(ShiftTemplate).filter(ShiftTemplate.id == sub.template_id).first()
        actividad = db.query(Activity).filter(Activity.id == template.activity_id).first() if template else None
        result.append({
            "subscription_id": sub.id,
            "actividad": actividad.name if actividad else None,
            "valid_to": str(sub.valid_to),
            "status": sub.status,
        })

    return result