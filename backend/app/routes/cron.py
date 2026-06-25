from __future__ import annotations

import asyncio
import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import joinedload, Session

from ..database import get_db
from ..models.activity import Activity
from ..models.payment import Payment
from ..models.shift_template import ShiftTemplate
from ..models.subscription import Subscription
from ..services import shift_service
from ..mail import send_subscription_payment_reminder
from ..time_override import business_today


router = APIRouter(prefix="/cron", tags=["cron"])


def _naive_datetime(value):
    if value is None:
        return None
    return value.replace(tzinfo=None) if getattr(value, "tzinfo", None) else value


@router.get("/backfill-instances")
def backfill_instances(request: Request, db: Session = Depends(get_db)):
    """Backfill ShiftInstances for all active templates.

    Intended to be triggered by Vercel Cron.
    Locally (non-Vercel) it is allowed for testing.
    """

    # On Vercel, only accept requests that look like Cron invocations.
    if os.getenv("VERCEL"):
        ua = (request.headers.get("user-agent") or "").lower()
        if "vercel-cron/1.0" not in ua:
            raise HTTPException(status_code=403, detail="Not authorized")

    templates = (
        db.query(ShiftTemplate)
        .join(Activity, ShiftTemplate.activity_id == Activity.id)
        .filter(Activity.is_active == True)
        .filter(ShiftTemplate.is_active == True)
        .all()
    )

    created_total = 0
    for template in templates:
        created = shift_service.create_instances_for_month(db, template, commit=False)
        created_total += len(created)

    db.commit()
    return {
        "today": str(date.today()),
        "templates": len(templates),
        "instances_created": created_total,
    }


@router.get("/send-pending-subscription-reminders")
def send_pending_subscription_reminders(request: Request, db: Session = Depends(get_db)):
    """Send a reminder mail for pending subscription payments on business day 10.

    Intended to be triggered by Vercel Cron or manually during testing with the
    simulated date header already supported by the app middleware.
    """
    if os.getenv("VERCEL"):
        ua = (request.headers.get("user-agent") or "").lower()
        if "vercel-cron/1.0" not in ua:
            raise HTTPException(status_code=403, detail="Not authorized")

    today = business_today()
    if today.day != 10:
        return {
            "today": str(today),
            "sent": 0,
            "skipped": 0,
            "message": "El recordatorio solo se envía el día 10.",
        }

    pending_payments = (
        db.query(Payment)
        .options(joinedload(Payment.user))
        .filter(
            Payment.type == "subscription",
            Payment.status == "pending",
        )
        .all()
    )

    sent = 0
    skipped = 0
    failed = 0
    matched_subscriptions = 0
    for payment in pending_payments:
        user = payment.user
        if not user or not user.email:
            skipped += 1
            continue

        matching_subscription = (
            db.query(Subscription)
            .options(joinedload(Subscription.template).joinedload(ShiftTemplate.activity))
            .filter(
                Subscription.user_id == user.id_user,
                Subscription.status == "active",
            )
            .order_by(Subscription.purchase_date.desc().nullslast(), Subscription.id.desc())
            .all()
        )

        subscription = None
        for candidate in matching_subscription:
            if not candidate.purchase_date:
                continue
            payment_date = _naive_datetime(payment.date)
            candidate_date = _naive_datetime(candidate.purchase_date)
            delta_seconds = abs((payment_date - candidate_date).total_seconds()) if payment_date and candidate_date else None
            if delta_seconds is not None and delta_seconds <= 5:
                subscription = candidate
                break

        if subscription is None:
            skipped += 1
            continue

        matched_subscriptions += 1
        template = subscription.template
        activity = template.activity if template else None
        if not activity:
            skipped += 1
            continue

        deporte = activity.name or "tu deporte"
        nombre = user.first_name or ""
        if user.last_name:
            nombre = f"{nombre} {user.last_name}".strip()
        if not nombre:
            nombre = user.email

        vencimiento = str(today) if today else (str(subscription.valid_to) if subscription.valid_to else None)
        try:
            asyncio.run(
                send_subscription_payment_reminder(
                    user.email,
                    nombre,
                    deporte,
                    vencimiento=vencimiento,
                )
            )
            sent += 1
        except Exception as exc:
            failed += 1
            print(f"Error enviando recordatorio a {user.email}: {exc}")

    return {
        "today": str(today),
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "pending_payments": len(pending_payments),
        "matched_subscriptions": matched_subscriptions,
    }
