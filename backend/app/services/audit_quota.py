"""Per-user monthly quotas for Audit, Quick Audit, and Snapshot (Access)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Audit, Snapshot, User

QuotaKind = Literal["audit", "quick", "snapshot"]

LIMIT_ATTR = {
    "audit": "monthly_audit_limit",
    "quick": "monthly_quick_audit_limit",
    "snapshot": "monthly_snapshot_limit",
}

LABEL = {
    "audit": "Audit",
    "quick": "Quick Audit",
    "snapshot": "Snapshot",
}


def month_start_utc(now: Optional[datetime] = None) -> datetime:
    n = now or datetime.utcnow()
    return datetime(n.year, n.month, 1)


def normalize_quota_limit(value: Optional[int], *, label: str = "Quota") -> Optional[int]:
    """None = unlimited. Reject negatives."""
    if value is None:
        return None
    n = int(value)
    if n < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} cannot be negative",
        )
    return n


def _is_quick_audit_row(full_results: Any) -> bool:
    if not isinstance(full_results, dict):
        return False
    return full_results.get("type") == "quick" or full_results.get("deck_mode") == "quick"


def monthly_counts(db: Session, user_id: int) -> dict[str, int]:
    """Usage for the current UTC calendar month."""
    start = month_start_utc()
    audit_used = 0
    quick_used = 0
    rows = (
        db.query(Audit.full_results)
        .filter(
            Audit.user_id == user_id,
            Audit.report_id.isnot(None),
            Audit.created_at >= start,
        )
        .all()
    )
    for (fr,) in rows:
        if _is_quick_audit_row(fr):
            quick_used += 1
        else:
            audit_used += 1

    snapshot_used = (
        db.query(Snapshot)
        .filter(Snapshot.user_id == user_id, Snapshot.created_at >= start)
        .count()
    )
    return {
        "audit": audit_used,
        "quick": quick_used,
        "snapshot": snapshot_used,
    }


def quota_payload(db: Session, user: User) -> dict[str, Any]:
    used = monthly_counts(db, user.id)
    return {
        "quota_period": "month",
        "quota_month_start": month_start_utc().date().isoformat(),
        "audit_count": used["audit"],
        "quick_audit_count": used["quick"],
        "snapshot_count": used["snapshot"],
        "monthly_audit_limit": getattr(user, "monthly_audit_limit", None),
        "monthly_quick_audit_limit": getattr(user, "monthly_quick_audit_limit", None),
        "monthly_snapshot_limit": getattr(user, "monthly_snapshot_limit", None),
        # Legacy aliases (prefer monthly_* above)
        "audit_limit": getattr(user, "monthly_audit_limit", None),
    }


def assert_can_create(db: Session, user: Optional[User], kind: QuotaKind) -> None:
    """Raise 429 when the operator hit their monthly Access quota for this kind."""
    if user is None:
        return
    attr = LIMIT_ATTR[kind]
    limit = getattr(user, attr, None)
    if limit is None:
        return
    used = monthly_counts(db, user.id)[kind]
    if used >= int(limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"{LABEL[kind]} monthly limit reached ({used}/{limit}). "
                "Ask Access to raise your quota, or wait until next month."
            ),
        )


# Back-compat names used by older call sites
def normalize_audit_limit(value: Optional[int]) -> Optional[int]:
    return normalize_quota_limit(value, label="Audit limit")


def user_audit_count(db: Session, user_id: int) -> int:
    return monthly_counts(db, user_id)["audit"]


def assert_can_create_audit(db: Session, user: Optional[User]) -> None:
    assert_can_create(db, user, "audit")
