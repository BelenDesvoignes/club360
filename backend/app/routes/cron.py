from __future__ import annotations

import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.activity import Activity
from ..models.shift_template import ShiftTemplate
from ..services import shift_service


router = APIRouter(prefix="/cron", tags=["cron"])


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
