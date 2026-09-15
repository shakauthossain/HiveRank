"""Track DataForSEO credit spend per run and cumulative per user."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import User


def as_cost(value: Any) -> float:
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, n), 6)


def format_credit(value: Any) -> str:
    n = as_cost(value)
    if n <= 0:
        return "—"
    if n < 0.01:
        return f"${n:.4f}"
    return f"${n:.4f}"


def add_user_credit(db: Session, user_id: Optional[int], cost: Any) -> float:
    """Increment the user's lifetime DFS credit usage. Returns applied amount."""
    amount = as_cost(cost)
    if not user_id or amount <= 0:
        return 0.0
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 0.0
    current = as_cost(getattr(user, "credit_used_usd", 0) or 0)
    user.credit_used_usd = round(current + amount, 6)
    return amount
