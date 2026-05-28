from __future__ import annotations

from contextvars import ContextVar
from datetime import date, datetime
from typing import Optional

# Per-request override of the "business date" (used for shifts/bookings/subscriptions).
# Auth/security timestamps (token expiry, reset codes) should continue using real time.
_business_today_override: ContextVar[Optional[date]] = ContextVar(
    "club360_business_today_override",
    default=None,
)


def set_business_today_override(value: date | None):
    return _business_today_override.set(value)


def reset_business_today_override(token) -> None:
    _business_today_override.reset(token)


def business_today() -> date:
    override = _business_today_override.get()
    return override or date.today()


def business_utcnow() -> datetime:
    override = _business_today_override.get()
    if not override:
        return datetime.utcnow()

    # Keep current time-of-day, but with the overridden date.
    now = datetime.utcnow()
    return datetime.combine(override, now.time())
