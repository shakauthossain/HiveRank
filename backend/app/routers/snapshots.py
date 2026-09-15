from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.database import get_db
from app.models import Snapshot, User
from app.schemas import (
    SnapshotApproveRequest,
    SnapshotCreateRequest,
    SnapshotUpdateRequest,
)
from app.services.dataforseo_client import DataForSeoClient, DataForSeoError
from app.services.audit_quota import assert_can_create
from app.services.snapshot_pptx import build_pptx
from app.services.snapshot_projections import apply_projection_edits
from app.services.snapshot_service import DEFAULT_BOOKING_URL, process_snapshot
from app.url_utils import extract_domain, is_valid_public_audit_url, normalize_url
import httpx
import os
import uuid

router = APIRouter(tags=["snapshots"])

REPORTS_DIR = os.path.join(os.getcwd(), "reports")
DAILY_SPEND_CAP = float(os.getenv("SNAPSHOT_DAILY_SPEND_CAP", "5"))
os.makedirs(REPORTS_DIR, exist_ok=True)


def _today_spend(db: Session) -> float:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.query(func.coalesce(func.sum(Snapshot.api_cost_usd), 0.0))
        .filter(Snapshot.created_at >= start)
        .scalar()
    )
    return float(total or 0)


@router.get("/dataforseo/status")
async def dataforseo_status(current_user: User = Depends(get_current_user)):
    """Verify REST API Access credentials without running a paid crawl."""
    async with httpx.AsyncClient() as client:
        try:
            dfs = DataForSeoClient.from_env(client)
            payload = await dfs.user_data()
        except DataForSeoError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    result = (payload.get("tasks") or [{}])[0].get("result")
    if isinstance(result, list):
        info = result[0] if result else {}
    elif isinstance(result, dict):
        info = result
    else:
        info = {}
    money = info.get("money") if isinstance(info, dict) else {}
    if not isinstance(money, dict):
        money = {}
    return {
        "ok": True,
        "auth": "HTTP Basic on https://api.dataforseo.com/v3 (API Access login + API password)",
        "login": info.get("login") if isinstance(info, dict) else None,
        "money_balance": money.get("balance"),
        "currency": money.get("currency") or "USD",
    }


def _serialize(snapshot: Snapshot, *, reused: bool = False) -> dict:
    return {
        "id": snapshot.snapshot_id,
        "status": snapshot.status,
        "progress": snapshot.progress,
        "error_message": snapshot.error_message,
        "prospect_url": snapshot.prospect_url,
        "prospect_domain": snapshot.prospect_domain,
        "competitor_mode": getattr(snapshot, "competitor_mode", None) or "auto",
        "competitor_urls": getattr(snapshot, "competitor_urls", None) or [],
        "thin_data": snapshot.thin_data,
        "api_cost_usd": snapshot.api_cost_usd,
        "usage_log": snapshot.usage_log,
        "payload": snapshot.payload,
        "top_fixes": snapshot.top_fixes,
        "booking_url": snapshot.booking_url,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "approved_at": snapshot.approved_at.isoformat() if snapshot.approved_at else None,
        "download_ready": bool(
            snapshot.status == "approved" and snapshot.pptx_filename
        ),
        "reused": reused,
    }


def _norm_host(domain: str) -> str:
    d = (domain or "").lower().strip()
    if d.startswith("www."):
        d = d[4:]
    return d


def _find_latest_snapshot_for_domain(db: Session, domain: str) -> Optional[Snapshot]:
    """Team-wide reuse: latest usable snapshot for this prospect domain."""
    want = _norm_host(domain)
    if not want:
        return None
    rows = (
        db.query(Snapshot)
        .filter(
            Snapshot.status.in_(("pending", "running", "review", "approved")),
        )
        .order_by(Snapshot.created_at.desc())
        .limit(200)
        .all()
    )
    for snap in rows:
        if _norm_host(snap.prospect_domain) != want:
            continue
        # Ready results need a payload; in-flight jobs are still reusable.
        if snap.status in ("review", "approved") and not snap.payload:
            continue
        return snap
    return None


def _get_snapshot(db: Session, snapshot_id: str) -> Snapshot:
    """Any signed-in operator can open a team snapshot (shared leave-behinds)."""
    snapshot = (
        db.query(Snapshot).filter(Snapshot.snapshot_id == snapshot_id).first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.post("/snapshots")
async def create_snapshot(
    request: SnapshotCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("snapshot")),
):
    prospect_url = normalize_url(request.prospect_url)
    ok, err = is_valid_public_audit_url(prospect_url)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Prospect: {err}")

    prospect_domain = extract_domain(prospect_url)
    if not prospect_domain:
        raise HTTPException(status_code=400, detail="Prospect domain is required.")

    # Reuse an existing team snapshot for this domain unless the operator forces a re-pull.
    if not request.force:
        existing = _find_latest_snapshot_for_domain(db, prospect_domain)
        if existing:
            return _serialize(existing, reused=True)

    fresh = db.query(User).filter(User.id == current_user.id).first()
    assert_can_create(db, fresh, "snapshot")

    mode = (request.competitor_mode or "auto").strip().lower()
    if mode not in ("auto", "manual"):
        raise HTTPException(
            status_code=400, detail="competitor_mode must be 'auto' or 'manual'."
        )

    manual_domains: list[str] = []
    raw_urls = list(request.competitor_urls or [])
    if request.competitor_url and not raw_urls:
        raw_urls = [request.competitor_url]
    if mode == "manual":
        for raw in raw_urls[:3]:
            if not raw or not str(raw).strip():
                continue
            c_url = normalize_url(str(raw).strip())
            c_ok, c_err = is_valid_public_audit_url(c_url)
            if not c_ok:
                raise HTTPException(status_code=400, detail=f"Competitor: {c_err}")
            c_domain = extract_domain(c_url)
            if not c_domain:
                raise HTTPException(
                    status_code=400, detail="Each competitor needs a valid domain."
                )
            if c_domain.lower().replace("www.", "") == prospect_domain.lower().replace(
                "www.", ""
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Competitor cannot be the same as the prospect.",
                )
            if c_domain not in manual_domains:
                manual_domains.append(c_domain)
        if not manual_domains:
            raise HTTPException(
                status_code=400,
                detail="Manual mode needs at least one competitor URL (up to 3).",
            )

    if _today_spend(db) >= DAILY_SPEND_CAP:
        raise HTTPException(
            status_code=429,
            detail=f"Daily DataForSEO spend cap (${DAILY_SPEND_CAP:.2f}) reached. Try again tomorrow or raise SNAPSHOT_DAILY_SPEND_CAP.",
        )

    first_comp = manual_domains[0] if manual_domains else ""
    snapshot = Snapshot(
        snapshot_id=str(uuid.uuid4()),
        user_id=current_user.id,
        prospect_url=prospect_url,
        prospect_domain=prospect_domain,
        competitor_url=f"https://{first_comp}" if first_comp else "",
        competitor_domain=first_comp,
        competitor_mode=mode,
        competitor_urls=manual_domains,
        location_code=request.location_code or 2840,
        language_code=(request.language_code or "en")[:8],
        status="pending",
        progress="Queued",
        booking_url=DEFAULT_BOOKING_URL,
        api_cost_usd=0,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    background_tasks.add_task(process_snapshot, snapshot.id)
    return _serialize(snapshot, reused=False)


@router.get("/me/snapshots")
def list_snapshots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Shared team history — every signed-in operator sees all snapshots."""
    rows = (
        db.query(Snapshot)
        .order_by(Snapshot.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": s.snapshot_id,
            "status": s.status,
            "prospect_domain": s.prospect_domain,
            "thin_data": s.thin_data,
            "api_cost_usd": s.api_cost_usd,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in rows
    ]


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _serialize(_get_snapshot(db, snapshot_id))


def _merge_projection_edits(payload: dict, edits: Optional[list]) -> dict:
    if not payload or not edits:
        return payload
    slide = payload.get("projections_slide") or {}
    payload = dict(payload)
    payload["projections_slide"] = apply_projection_edits(
        slide, [e.model_dump() if hasattr(e, "model_dump") else e for e in edits]
    )
    return payload


@router.patch("/snapshots/{snapshot_id}")
def update_snapshot(
    snapshot_id: str,
    request: SnapshotUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snapshot = _get_snapshot(db, snapshot_id)
    if snapshot.status not in ("review", "approved"):
        raise HTTPException(
            status_code=400, detail="Wait until the data pull is ready to edit."
        )
    if request.top_fixes is not None:
        cleaned = [f.strip() for f in request.top_fixes if f and f.strip()]
        snapshot.top_fixes = cleaned[:8]
        if snapshot.payload:
            payload = dict(snapshot.payload)
            payload["top_fixes"] = snapshot.top_fixes
            snapshot.payload = payload
    if request.booking_url is not None:
        snapshot.booking_url = request.booking_url.strip() or DEFAULT_BOOKING_URL
        if snapshot.payload:
            payload = dict(snapshot.payload)
            payload["booking_url"] = snapshot.booking_url
            snapshot.payload = payload
    if request.projection_rows is not None and snapshot.payload:
        snapshot.payload = _merge_projection_edits(snapshot.payload, request.projection_rows)
    db.commit()
    db.refresh(snapshot)
    return _serialize(snapshot)


@router.post("/snapshots/{snapshot_id}/approve")
def approve_snapshot(
    snapshot_id: str,
    request: SnapshotApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snapshot = _get_snapshot(db, snapshot_id)
    if snapshot.status not in ("review", "approved"):
        raise HTTPException(
            status_code=400, detail="This snapshot is not ready to approve."
        )
    if request.top_fixes is not None:
        snapshot.top_fixes = [f.strip() for f in request.top_fixes if f and f.strip()][:8]
    if request.booking_url is not None:
        snapshot.booking_url = request.booking_url.strip() or DEFAULT_BOOKING_URL

    payload = dict(snapshot.payload or {})
    payload["top_fixes"] = snapshot.top_fixes or payload.get("top_fixes") or []
    payload["booking_url"] = snapshot.booking_url or DEFAULT_BOOKING_URL
    if request.projection_rows is not None:
        payload = _merge_projection_edits(payload, request.projection_rows)
    payload["prospect_domain"] = snapshot.prospect_domain
    payload["thin_data"] = snapshot.thin_data
    payload["date"] = payload.get("date") or datetime.utcnow().strftime("%d %B %Y")
    snapshot.payload = payload

    filename = f"{snapshot.snapshot_id}_snapshot.pptx"
    output_path = os.path.join(REPORTS_DIR, filename)
    try:
        build_pptx(payload, output_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not build the deck: {exc}")

    snapshot.pptx_filename = filename
    snapshot.status = "approved"
    snapshot.approved_at = datetime.utcnow()
    snapshot.progress = "Approved"
    db.commit()
    db.refresh(snapshot)
    return _serialize(snapshot)


@router.get("/snapshots/{snapshot_id}/download")
def download_snapshot(
    snapshot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snapshot = _get_snapshot(db, snapshot_id)
    if snapshot.status != "approved" or not snapshot.pptx_filename:
        raise HTTPException(
            status_code=400, detail="Approve the snapshot before downloading."
        )
    path = os.path.join(REPORTS_DIR, snapshot.pptx_filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Deck file is missing. Approve again.")
    download_name = f"NH-SEO-Snapshot-{snapshot.prospect_domain}.pptx"
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=download_name,
    )
