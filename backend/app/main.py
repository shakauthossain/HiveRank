import asyncio
import os
import uuid
from datetime import timedelta
from typing import List, Optional

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_admin_actor,
    get_current_user,
    get_optional_user,
    get_password_hash,
    preset_permissions,
    require_permission,
    role_label_from_permissions,
    user_permissions,
    verify_password,
)
from app.database import Base, engine, get_db, SessionLocal, close_db
from app.models import Audit, BulkJob, Snapshot, User
from app.routers.chatbot import router as chatbot_router
from app.routers.snapshots import router as snapshots_router
from app.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ProfileUpdate,
    ReportType,
    UserPermissionsUpdate,
)
from app.services.credits import add_user_credit, as_cost
from app.services.audit_quota import (
    assert_can_create,
    normalize_quota_limit,
    quota_payload,
)
from app.services.bulk_service import process_bulk_audit
from app.services.analyze_deck import generate_analyze_deck
from app.services.pdf_service import generate_pdf_safe
from app.services.seo_service import scrape_rankmath_async
from app.services.speed_service import fetch_pagespeed_data_sync, parse_pagespeed_data
from app.url_utils import (
    extract_domain,
    format_speed_score_for_storage,
    is_valid_public_audit_url,
    normalize_url,
    resolved_url_for_list,
    resolved_url_for_storage,
)
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

# Initialize Database
Base.metadata.create_all(bind=engine)

# Ensure Database schema is up-to-date (Migration)
with engine.connect() as conn:
    try:
        from sqlalchemy import text
        # Migration for BulkJob
        conn.execute(text("ALTER TABLE bulk_jobs ADD COLUMN IF NOT EXISTS total_count INTEGER DEFAULT 0;"))
        conn.execute(text("ALTER TABLE bulk_jobs ADD COLUMN IF NOT EXISTS processed_count INTEGER DEFAULT 0;"))
        
        # Migration for Audit (Legacy/Missing full_results)
        conn.execute(text("ALTER TABLE audits ADD COLUMN IF NOT EXISTS full_results JSONB;"))
        Snapshot.__table__.create(bind=conn, checkfirst=True)
        conn.execute(
            text(
                "ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS competitor_mode VARCHAR DEFAULT 'auto';"
            )
        )
        conn.execute(
            text("ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS competitor_urls JSONB;")
        )
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR;")
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_analyze BOOLEAN DEFAULT TRUE;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_snapshot BOOLEAN DEFAULT TRUE;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_bulk BOOLEAN DEFAULT TRUE;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_access BOOLEAN DEFAULT FALSE;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_quick_audit BOOLEAN DEFAULT TRUE;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS credit_used_usd DOUBLE PRECISION DEFAULT 0;"
            )
        )
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS audit_limit INTEGER;")
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_audit_limit INTEGER;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_quick_audit_limit INTEGER;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_snapshot_limit INTEGER;"
            )
        )
        # One-time: copy legacy lifetime audit_limit into monthly audit quota when unset
        conn.execute(
            text(
                """
                UPDATE users
                SET monthly_audit_limit = audit_limit
                WHERE monthly_audit_limit IS NULL
                  AND audit_limit IS NOT NULL;
                """
            )
        )
        conn.execute(
            text(
                "ALTER TABLE audits ADD COLUMN IF NOT EXISTS api_cost_usd DOUBLE PRECISION DEFAULT 0;"
            )
        )
        conn.execute(
            text("ALTER TABLE audits ADD COLUMN IF NOT EXISTS usage_log JSONB;")
        )
        conn.execute(
            text("UPDATE users SET can_analyze = TRUE WHERE can_analyze IS NULL;")
        )
        conn.execute(
            text("UPDATE users SET can_snapshot = TRUE WHERE can_snapshot IS NULL;")
        )
        conn.execute(text("UPDATE users SET can_bulk = TRUE WHERE can_bulk IS NULL;"))
        conn.execute(
            text("UPDATE users SET can_access = FALSE WHERE can_access IS NULL;")
        )
        conn.execute(
            text(
                "UPDATE users SET can_quick_audit = TRUE WHERE can_quick_audit IS NULL;"
            )
        )
        conn.execute(
            text(
                "UPDATE users SET credit_used_usd = 0 WHERE credit_used_usd IS NULL;"
            )
        )
        conn.execute(
            text("UPDATE audits SET api_cost_usd = 0 WHERE api_cost_usd IS NULL;")
        )
        # One-time backfill: pull cost out of quick-audit JSON when column is still 0
        conn.execute(
            text(
                """
                UPDATE audits
                SET api_cost_usd = COALESCE(
                    NULLIF((full_results->>'api_cost_usd')::float, 0),
                    api_cost_usd,
                    0
                )
                WHERE full_results IS NOT NULL
                  AND full_results ? 'api_cost_usd'
                  AND COALESCE(api_cost_usd, 0) = 0;
                """
            )
        )
        # Rebuild lifetime user credit from audits + snapshots when still zero
        conn.execute(
            text(
                """
                UPDATE users u
                SET credit_used_usd = COALESCE(agg.total, 0)
                FROM (
                  SELECT user_id, ROUND(SUM(cost)::numeric, 6) AS total
                  FROM (
                    SELECT user_id, COALESCE(api_cost_usd, 0) AS cost FROM audits
                    WHERE user_id IS NOT NULL
                    UNION ALL
                    SELECT user_id, COALESCE(api_cost_usd, 0) AS cost FROM snapshots
                    WHERE user_id IS NOT NULL
                  ) t
                  GROUP BY user_id
                ) agg
                WHERE u.id = agg.user_id
                  AND COALESCE(u.credit_used_usd, 0) = 0
                  AND agg.total > 0;
                """
            )
        )

        conn.commit()
        print("--- SUCCESS: Database migrations completed ---")
    except Exception as e:
        print(f"--- WARNING: Migration check failed: {e} ---")

app = FastAPI(title="SEO & Speed Analysis API (Enterprise)")
app.include_router(snapshots_router)
app.include_router(chatbot_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://seo-tool.riseo.online",
        "http://seo-tool.riseo.online",
        "http://localhost:3000",
        "http://localhost:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS_DIR = os.path.join(os.getcwd(), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY")
BASE_URL = os.getenv("BASE_URL")
if BASE_URL:
    BASE_URL = BASE_URL.rstrip("/")

# --- AUTH ROUTES ---

# --- ADMIN ROUTES ---


@app.post("/admin/create-user", status_code=status.HTTP_201_CREATED)
def admin_create_user(
    email: str,
    password: str,
    preset: str = "operator",
    display_name: Optional[str] = None,
    monthly_audit_limit: Optional[int] = None,
    monthly_quick_audit_limit: Optional[int] = None,
    monthly_snapshot_limit: Optional[int] = None,
    db: Session = Depends(get_db),
    admin_actor: str = Depends(get_admin_actor),
):
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    flags = preset_permissions(preset)
    new_user = User(
        email=email,
        hashed_password=get_password_hash(password),
        display_name=(display_name or "").strip() or None,
        monthly_audit_limit=normalize_quota_limit(
            monthly_audit_limit, label="Audit monthly limit"
        ),
        monthly_quick_audit_limit=normalize_quota_limit(
            monthly_quick_audit_limit, label="Quick Audit monthly limit"
        ),
        monthly_snapshot_limit=normalize_quota_limit(
            monthly_snapshot_limit, label="Snapshot monthly limit"
        ),
        **flags,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "message": f"User {email} created successfully by admin {admin_actor}",
        "permissions": user_permissions(new_user),
        "role": role_label_from_permissions(user_permissions(new_user)),
        **quota_payload(db, new_user),
    }


@app.get("/admin/users")
def admin_list_users(
    db: Session = Depends(get_db), admin_actor: str = Depends(get_admin_actor)
):
    users = db.query(User).order_by(User.id.asc()).all()
    result = []
    for u in users:
        perms = user_permissions(u)
        result.append(
            {
                "id": u.id,
                "email": u.email,
                "display_name": getattr(u, "display_name", None),
                "credit_used_usd": as_cost(getattr(u, "credit_used_usd", 0)),
                "permissions": perms,
                "role": role_label_from_permissions(perms),
                **quota_payload(db, u),
            }
        )
    return result


@app.patch("/admin/users/{user_id}/permissions")
def admin_update_permissions(
    user_id: int,
    body: UserPermissionsUpdate,
    db: Session = Depends(get_db),
    admin_actor: str = Depends(get_admin_actor),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.can_analyze = bool(body.can_analyze)
    user.can_snapshot = bool(body.can_snapshot)
    user.can_bulk = bool(body.can_bulk)
    user.can_quick_audit = bool(body.can_quick_audit)
    user.can_access = bool(body.can_access)
    if body.display_name is not None:
        user.display_name = body.display_name.strip() or None
    payload = body.model_dump(exclude_unset=True)
    if "monthly_audit_limit" in payload:
        user.monthly_audit_limit = normalize_quota_limit(
            payload.get("monthly_audit_limit"), label="Audit monthly limit"
        )
    if "monthly_quick_audit_limit" in payload:
        user.monthly_quick_audit_limit = normalize_quota_limit(
            payload.get("monthly_quick_audit_limit"),
            label="Quick Audit monthly limit",
        )
    if "monthly_snapshot_limit" in payload:
        user.monthly_snapshot_limit = normalize_quota_limit(
            payload.get("monthly_snapshot_limit"),
            label="Snapshot monthly limit",
        )
    db.commit()
    db.refresh(user)
    perms = user_permissions(user)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "permissions": perms,
        "role": role_label_from_permissions(perms),
        "updated_by": admin_actor,
        **quota_payload(db, user),
    }


@app.delete("/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_actor: str = Depends(get_admin_actor),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Delete user's audits first
    db.query(Audit).filter(Audit.user_id == user_id).delete()
    db.query(BulkJob).filter(BulkJob.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"message": f"User {user.email} deleted successfully by {admin_actor}"}


@app.get("/admin/stats")
def admin_stats(
    db: Session = Depends(get_db), admin_actor: str = Depends(get_admin_actor)
):
    total_users = db.query(User).count()
    total_audits = db.query(Audit).count()
    total_jobs = db.query(BulkJob).count()
    return {
        "total_users": total_users,
        "total_audits": total_audits,
        "total_bulk_jobs": total_jobs,
        "actor": admin_actor,
    }


@app.post("/token")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# --- AUDIT ROUTES ---


def _audit_has_seo(full_results: Optional[dict]) -> bool:
    if not isinstance(full_results, dict):
        return False
    seo = full_results.get("seo")
    if not isinstance(seo, dict) or not seo:
        return False
    score = seo.get("seo_score")
    if score not in (None, "", "N/A"):
        return True
    return bool(seo.get("categories") or seo.get("seo_tests") or seo.get("items"))


def _audit_has_speed(full_results: Optional[dict]) -> bool:
    if not isinstance(full_results, dict):
        return False
    speed = full_results.get("speed")
    if not isinstance(speed, dict) or not speed:
        return False
    if isinstance(speed.get("mobile"), dict) and speed.get("mobile"):
        return True
    if isinstance(speed.get("desktop"), dict) and speed.get("desktop"):
        return True
    score = speed.get("perf_score")
    if score not in (None, "", "N/A"):
        return True
    metrics = speed.get("metrics")
    return isinstance(metrics, dict) and any(
        v not in (None, "", "N/A") for v in metrics.values()
    )


def _is_quick_audit(fr: Optional[dict]) -> bool:
    if not isinstance(fr, dict):
        return False
    return fr.get("type") == "quick" or fr.get("deck_mode") == "quick"


def _audit_covers_report_type(audit: Audit, report_type: ReportType) -> bool:
    fr = audit.full_results if isinstance(audit.full_results, dict) else None
    if report_type == ReportType.QUICK:
        return _is_quick_audit(fr)
    if _is_quick_audit(fr):
        return False
    if report_type == ReportType.SEO:
        return _audit_has_seo(fr)
    if report_type == ReportType.SPEED:
        return _audit_has_speed(fr)
    return _audit_has_seo(fr) and _audit_has_speed(fr)


def _audit_api_payload(audit: Audit, *, reused: bool = False) -> dict:
    """Shape stored audit rows the same way /analyze and /audits/{id} return."""
    report_id = audit.report_id
    fr = audit.full_results if isinstance(audit.full_results, dict) else {}
    display_url = resolved_url_for_list(audit.url, audit.full_results)

    if _is_quick_audit(fr):
        pptx = fr.get("pptx_filename") or f"{report_id}_quick.pptx"
        cost = as_cost(
            getattr(audit, "api_cost_usd", None)
            if getattr(audit, "api_cost_usd", None) is not None
            else fr.get("api_cost_usd")
        )
        return {
            "id": report_id,
            "url": display_url,
            "type": "quick",
            "api_cost_usd": cost,
            "quick": {
                "health": fr.get("health") or (fr.get("payload") or {}).get("health"),
                "performance_slide": fr.get("performance_slide")
                or (fr.get("payload") or {}).get("performance_slide"),
                "top_fixes": fr.get("top_fixes")
                or (fr.get("payload") or {}).get("top_fixes")
                or [],
                "api_cost_usd": cost,
                "domain": fr.get("domain")
                or (fr.get("payload") or {}).get("prospect_domain"),
            },
            "quick_report_url": f"{BASE_URL}/reports/{pptx}" if BASE_URL else f"/reports/{pptx}",
            "reused": reused,
        }

    seo_data = fr.get("seo", {}) if fr else {}
    speed_data = fr.get("speed", {}) if fr else {}

    seo_tests = []
    for cat in seo_data.get("categories", []) if isinstance(seo_data, dict) else []:
        seo_tests.extend(cat.get("items", []))

    speed_tests = []
    mobile_block = (
        speed_data.get("mobile") if isinstance(speed_data.get("mobile"), dict) else {}
    )
    desktop_block = (
        speed_data.get("desktop") if isinstance(speed_data.get("desktop"), dict) else {}
    )
    for block in (mobile_block, desktop_block, speed_data):
        if not isinstance(block, dict):
            continue
        for cat in block.get("categories") or []:
            speed_tests.extend(cat.get("items") or [])

    metrics_src = mobile_block or speed_data
    payload = {
        "id": report_id,
        "url": display_url,
        "type": "both",
        "seo": {
            **(seo_data if isinstance(seo_data, dict) else {}),
            "seo_score": audit.seo_score,
            "seo_tests": seo_tests,
        },
        "speed": {
            **(speed_data if isinstance(speed_data, dict) else {}),
            "perf_score": audit.speed_score,
            "metrics": {
                "fcp": metrics_src.get("fcp", "N/A") if isinstance(metrics_src, dict) else "N/A",
                "lcp": metrics_src.get("lcp", "N/A") if isinstance(metrics_src, dict) else "N/A",
                "cls": metrics_src.get("cls", "N/A") if isinstance(metrics_src, dict) else "N/A",
                "tbt": metrics_src.get("tbt", "N/A") if isinstance(metrics_src, dict) else "N/A",
                "si": metrics_src.get("si", "N/A") if isinstance(metrics_src, dict) else "N/A",
                "tti": metrics_src.get("tti", "N/A") if isinstance(metrics_src, dict) else "N/A",
            },
            "speed_tests": speed_tests,
        },
        "seo_report_url": f"{BASE_URL}/reports/{report_id}_seo.html",
        "speed_report_url": f"{BASE_URL}/reports/{report_id}_speed.html",
        "api_cost_usd": as_cost(getattr(audit, "api_cost_usd", 0)),
        "reused": reused,
    }
    return payload


def _find_latest_audit_for_domain(
    db: Session,
    domain: str,
    report_type: Optional[ReportType] = None,
) -> Optional[Audit]:
    if not domain:
        return None
    want = extract_domain(domain) or domain.lower()
    rows = (
        db.query(Audit)
        .filter(Audit.report_id.isnot(None), Audit.full_results.isnot(None))
        .order_by(Audit.created_at.desc())
        .limit(400)
        .all()
    )
    for audit in rows:
        stored = resolved_url_for_list(audit.url, audit.full_results)
        if extract_domain(stored) != want and extract_domain(audit.url) != want:
            continue
        if report_type is not None and not _audit_covers_report_type(audit, report_type):
            continue
        return audit
    return None


@app.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perms = user_permissions(current_user)
    # Re-load so monthly_* columns are current
    user = db.query(User).filter(User.id == current_user.id).first() or current_user
    return {
        "id": user.id,
        "email": user.email,
        "display_name": getattr(user, "display_name", None),
        "permissions": perms,
        "role": role_label_from_permissions(perms),
        "credit_used_usd": as_cost(getattr(user, "credit_used_usd", 0)),
        **quota_payload(db, user),
    }


@app.patch("/me")
def update_me(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update display name and/or password. Email cannot be changed."""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.display_name is not None:
        user.display_name = body.display_name.strip() or None

    changing_password = body.new_password is not None and body.new_password != ""
    if changing_password:
        if not body.current_password:
            raise HTTPException(
                status_code=400, detail="Current password is required"
            )
        if not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(
                status_code=400, detail="Current password is incorrect"
            )
        new_pw = body.new_password.strip()
        if len(new_pw) < 5:
            raise HTTPException(
                status_code=400,
                detail="New password must be at least 5 characters",
            )
        user.hashed_password = get_password_hash(new_pw)

    db.commit()
    db.refresh(user)
    perms = user_permissions(user)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "permissions": perms,
        "role": role_label_from_permissions(perms),
        "credit_used_usd": as_cost(getattr(user, "credit_used_usd", 0)),
        "password_updated": changing_password,
    }


@app.get("/me/audits")
def get_user_audits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Shared team history — every signed-in operator sees all audits."""
    audits = []
    rows = (
        db.query(Audit, User.email)
        .outerjoin(User, Audit.user_id == User.id)
        .filter(Audit.report_id.isnot(None))
        .order_by(Audit.created_at.desc())
        .limit(200)
        .all()
    )
    for a, owner_email in rows:
        fr = a.full_results if isinstance(a.full_results, dict) else {}
        audit_type = "quick" if _is_quick_audit(fr) else "both"
        cost = as_cost(getattr(a, "api_cost_usd", None))
        if cost <= 0 and isinstance(fr, dict):
            cost = as_cost(fr.get("api_cost_usd"))
        audits.append(
            {
                "report_id": a.report_id,
                "url": resolved_url_for_list(a.url, a.full_results),
                "seo_score": a.seo_score,
                "speed_score": a.speed_score,
                "type": audit_type,
                "api_cost_usd": cost,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "owner_email": owner_email,
                "owner_id": a.user_id,
            }
        )
    return audits


@app.get("/audits/lookup")
def lookup_audit_by_url(
    url: str,
    report_type: ReportType = ReportType.BOTH,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the latest shared audit for a domain, if any."""
    domain = extract_domain(normalize_url(url))
    audit = _find_latest_audit_for_domain(db, domain, report_type)
    if not audit:
        return {"found": False, "domain": domain}
    owner = db.query(User).filter(User.id == audit.user_id).first() if audit.user_id else None
    return {
        "found": True,
        "domain": domain,
        "report_id": audit.report_id,
        "url": resolved_url_for_list(audit.url, audit.full_results),
        "seo_score": audit.seo_score,
        "speed_score": audit.speed_score,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "owner_email": owner.email if owner else None,
    }


@app.post("/analyze/bulk")
async def bulk_analyze(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("bulk")),
    db: Session = Depends(get_db),
):
    # Save uploaded file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(REPORTS_DIR, f"upload_{file_id}{ext}")

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Create Job
    job = BulkJob(
        user_id=current_user.id, input_filename=file.filename, status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        process_bulk_audit, db, job.id, file_path, current_user.id
    )

    return {"job_id": job.id, "status": "queued"}


@app.get("/bulk/status/{job_id}")
def get_bulk_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(BulkJob)
        .filter(BulkJob.id == job_id, BulkJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "user_id": job.user_id,
        "input_filename": job.input_filename,
        "output_filename": job.output_filename,
        "status": job.status,
        "total_count": job.total_count,
        "processed_count": job.processed_count,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@app.get("/me/bulk-jobs")
def list_my_bulk_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(BulkJob)
        .filter(BulkJob.user_id == current_user.id)
        .order_by(BulkJob.created_at.desc())
        .all()
    )
    return [
        {
            "id": j.id,
            "input_filename": j.input_filename,
            "output_filename": j.output_filename,
            "status": j.status,
            "total_count": j.total_count,
            "processed_count": j.processed_count,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


@app.get("/bulk/jobs/{job_id}/download")
def download_bulk_job_csv(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(BulkJob)
        .filter(BulkJob.id == job_id, BulkJob.user_id == current_user.id)
        .first()
    )
    if not job or job.status != "completed" or not job.output_filename:
        raise HTTPException(
            status_code=404, detail="Completed export not found for this job"
        )
    file_path = os.path.join(REPORTS_DIR, job.output_filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Export file missing on server")
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename=job.output_filename,
    )


# --- LEGACY / SINGLE ROUTES (Updated to save to DB) ---


@app.post("/analyze")
async def analyze_website(
    request: AnalysisRequest,
    current_user: Optional[User] = Depends(get_optional_user),
):
    url = normalize_url(request.url)
    ok, url_err = is_valid_public_audit_url(url)
    if not ok:
        raise HTTPException(status_code=400, detail=url_err)

    domain = extract_domain(url)
    report_type = request.report_type
    perms = user_permissions(current_user) if current_user is not None else {}

    if current_user is not None:
        if report_type == ReportType.QUICK:
            if not perms.get("quick_audit"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Missing permission: quick_audit",
                )
        elif not perms.get("analyze"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing permission: analyze",
            )

    # Reuse an existing team audit for this domain unless the operator forces a re-run.
    # Only reuse when the stored result covers the requested report type (seo / speed / both).
    if not request.force:
        db_lookup = SessionLocal()
        try:
            existing = _find_latest_audit_for_domain(
                db_lookup, domain, request.report_type
            )
            if existing and existing.full_results:
                print(
                    f"--- INFO: Reusing existing audit {existing.report_id} "
                    f"for {domain} ({request.report_type.value}) ---"
                )
                return _audit_api_payload(existing, reused=True)
        finally:
            close_db(db_lookup)

    # New audit run — enforce Access monthly quotas (separate for Audit vs Quick)
    if current_user is not None:
        db_quota = SessionLocal()
        try:
            fresh = db_quota.query(User).filter(User.id == current_user.id).first()
            kind = "quick" if report_type == ReportType.QUICK else "audit"
            assert_can_create(db_quota, fresh, kind)
        finally:
            close_db(db_quota)

    if report_type == ReportType.QUICK:
        from app.services.quick_audit_service import run_quick_audit

        print(f"--- INFO: Starting Quick Audit for {url} ---")
        try:
            result = await run_quick_audit(url, reports_dir=REPORTS_DIR)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            print(f"--- ERROR: Quick Audit failed for {url}: {exc} ---")
            raise HTTPException(
                status_code=500, detail=f"Quick Audit failed: {exc}"
            ) from exc

        report_id = result["id"]
        cost = as_cost(result.get("api_cost_usd"))
        try:
            db = SessionLocal()
            try:
                new_audit = Audit(
                    url=url,
                    seo_score="Quick",
                    speed_score="—",
                    report_id=report_id,
                    api_cost_usd=cost,
                    usage_log=result.get("usage_log"),
                    full_results={
                        "type": "quick",
                        "deck_mode": "quick",
                        "domain": result.get("domain"),
                        "payload": result.get("payload"),
                        "health": result.get("health"),
                        "performance_slide": result.get("performance_slide"),
                        "top_fixes": result.get("top_fixes") or [],
                        "api_cost_usd": cost,
                        "pptx_filename": result.get("pptx_filename"),
                    },
                    user_id=current_user.id if current_user else None,
                )
                db.add(new_audit)
                if current_user is not None:
                    add_user_credit(db, current_user.id, cost)
                db.commit()
                print(f"--- SUCCESS: Quick Audit saved for {url} (credit ${cost}) ---")
            except Exception as db_err:
                try:
                    db.rollback()
                except Exception:
                    pass
                print(f"--- WARNING: Could not save Quick Audit: {db_err} ---")
            finally:
                close_db(db)
        except Exception as e:
            print(f"--- WARNING: Could not prepare Quick Audit record: {e} ---")

        pptx = result.get("pptx_filename") or f"{report_id}_quick.pptx"
        return {
            "id": report_id,
            "url": url,
            "type": "quick",
            "api_cost_usd": cost,
            "quick": {
                "health": result.get("health"),
                "performance_slide": result.get("performance_slide"),
                "top_fixes": result.get("top_fixes") or [],
                "api_cost_usd": cost,
                "domain": result.get("domain"),
            },
            "quick_report_url": f"{BASE_URL}/reports/{pptx}" if BASE_URL else f"/reports/{pptx}",
            "reused": False,
        }

    print(f"--- INFO: Starting analysis for {url} ---")
    report_id = str(uuid.uuid4())

    # 1. SEO Analysis
    seo_data = {}
    if report_type in [ReportType.SEO, ReportType.BOTH]:
        seo_data = await scrape_rankmath_async(url)

    # 2. Speed Analysis
    speed_data = {}
    if report_type in [ReportType.SPEED, ReportType.BOTH]:
        print(f"--- INFO: Fetching Speed data (Mobile & Desktop) for {url} ---")
        
        # Fetch both in parallel
        mobile_task = asyncio.to_thread(fetch_pagespeed_data_sync, url, PAGESPEED_API_KEY, "mobile")
        desktop_task = asyncio.to_thread(fetch_pagespeed_data_sync, url, PAGESPEED_API_KEY, "desktop")
        raw_mobile, raw_desktop = await asyncio.gather(mobile_task, desktop_task)

        if raw_mobile or raw_desktop:
            print(f"--- SUCCESS: Speed data fetched for {url} ---")
            
            # Parse both
            mob_res = parse_pagespeed_data(raw_mobile, url, "mobile") if raw_mobile else {}
            dsk_res = parse_pagespeed_data(raw_desktop, url, "desktop") if raw_desktop else {}
            
            # Combine into a unified structure
            speed_data = {
                "mobile": mob_res,
                "desktop": dsk_res,
                "perf_score": mob_res.get("perf_score", "N/A"), # Default fallback
                "perf_score_desktop": dsk_res.get("perf_score", "N/A")
            }
        else:
            print(f"--- WARNING: Speed data FETCH FAILED for {url} ---")

    deck_html = generate_analyze_deck(seo_data, speed_data)
    if report_type in [ReportType.SEO, ReportType.BOTH] and deck_html:
        with open(
            os.path.join(REPORTS_DIR, f"{report_id}_seo.html"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(deck_html)
        await generate_pdf_safe(deck_html, os.path.join(REPORTS_DIR, f"{report_id}_seo.pdf"))
    if report_type in [ReportType.SPEED, ReportType.BOTH] and deck_html:
        with open(
            os.path.join(REPORTS_DIR, f"{report_id}_speed.html"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(deck_html)
        await generate_pdf_safe(
            deck_html, os.path.join(REPORTS_DIR, f"{report_id}_speed.pdf")
        )

    # Save to DB (Defensive)
    try:
        full_results = {"seo": seo_data, "speed": speed_data}
        stored_url = resolved_url_for_storage(url, speed_data)
        stored_speed = format_speed_score_for_storage(speed_data)
        db = SessionLocal()
        try:
            new_audit = Audit(
                url=stored_url,
                seo_score=str(seo_data.get("seo_score", "N/A")),
                speed_score=stored_speed,
                report_id=report_id,
                full_results=full_results,
                api_cost_usd=0.0,
                user_id=current_user.id if current_user else None,
            )
            db.add(new_audit)
            db.commit()
            print(f"--- SUCCESS: Audit saved to history for {url} ---")
        except Exception as db_err:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"--- WARNING: Could not save audit to history: {db_err} ---")
        finally:
            close_db(db)
    except Exception as e:
        print(f"--- WARNING: Could not prepare audit record: {e} ---")

    # Flatten for frontend dashboard
    seo_tests = []
    for cat in seo_data.get("categories", []):
        seo_tests.extend(cat.get("items", []))

    speed_tests = []
    mobile_block = speed_data.get("mobile") if isinstance(speed_data.get("mobile"), dict) else {}
    desktop_block = speed_data.get("desktop") if isinstance(speed_data.get("desktop"), dict) else {}
    for block in (mobile_block, desktop_block, speed_data):
        if not isinstance(block, dict):
            continue
        for cat in block.get("categories") or []:
            speed_tests.extend(cat.get("items") or [])

    metrics_src = mobile_block or speed_data
    return {
        "id": report_id,
        "seo": {
            **seo_data,
            "seo_score": seo_data.get("seo_score", "N/A"),
            "seo_tests": seo_tests,
        },
        "speed": {
            **speed_data,
            "perf_score": speed_data.get("perf_score", "N/A"),
            "metrics": {
                "fcp": metrics_src.get("fcp", "N/A"),
                "lcp": metrics_src.get("lcp", "N/A"),
                "cls": metrics_src.get("cls", "N/A"),
                "tbt": metrics_src.get("tbt", "N/A"),
                "si": metrics_src.get("si", "N/A"),
                "tti": metrics_src.get("tti", "N/A"),
            },
            "speed_tests": speed_tests,
        },
        "seo_report_url": f"{BASE_URL}/reports/{report_id}_seo.html",
        "speed_report_url": f"{BASE_URL}/reports/{report_id}_speed.html",
        "api_cost_usd": 0.0,
        "reused": False,
    }


@app.get("/reports/{filename}")
async def get_report_file(filename: str, db: Session = Depends(get_db)):
    file_path = os.path.join(REPORTS_DIR, filename)
    is_html = filename.endswith(".html")
    is_pdf = filename.endswith(".pdf")

    # Only HTML reports can be checked for broken text content
    needs_regen = False
    if os.path.exists(file_path):
        if is_html:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(200)
            if "Error generating report" in content:
                needs_regen = True
    elif is_html or is_pdf:
        needs_regen = True

    if needs_regen:
        base = filename.removesuffix(".html").removesuffix(".pdf")
        parts = base.rsplit("_", 1)
        if len(parts) == 2:
            report_id, report_type = parts[0], parts[1]
            audit = db.query(Audit).filter(Audit.report_id == report_id).first()
            if audit and audit.full_results:
                try:
                    html = None
                    if report_type in ("seo", "speed"):
                        html = generate_analyze_deck(
                            audit.full_results.get("seo", {}),
                            audit.full_results.get("speed", {}),
                        )
                    if html:
                        html_path = os.path.join(
                            REPORTS_DIR, f"{report_id}_{report_type}.html"
                        )
                        pdf_path = os.path.join(
                            REPORTS_DIR, f"{report_id}_{report_type}.pdf"
                        )
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(html)
                        if is_pdf or not os.path.exists(pdf_path):
                            await generate_pdf_safe(html, pdf_path)
                except Exception as regen_err:
                    print(f"--- WARNING: Could not regenerate report {filename}: {regen_err} ---")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    if is_pdf:
        media_type = "application/pdf"
    elif filename.endswith(".pptx"):
        media_type = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    else:
        media_type = None
    return FileResponse(file_path, media_type=media_type)


@app.post("/admin/regenerate-reports")
def regenerate_all_broken_reports(
    db: Session = Depends(get_db),
    admin_actor: str = Depends(get_admin_actor),
):
    """Regenerate all HTML report files that contain errors, using saved DB data."""
    fixed = 0
    skipped = 0
    failed = 0

    audits = db.query(Audit).filter(Audit.full_results.isnot(None)).all()
    for audit in audits:
        if not audit.report_id or not audit.full_results:
            skipped += 1
            continue

        targets = []
        for report_type in ("seo", "speed"):
            filename = f"{audit.report_id}_{report_type}.html"
            file_path = os.path.join(REPORTS_DIR, filename)
            data_key = report_type
            needs_regen = False
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    snippet = f.read(200)
                if "Error generating report" in snippet:
                    needs_regen = True
            else:
                needs_regen = True

            if not needs_regen:
                continue

            data = audit.full_results.get(data_key, {})
            if not data:
                skipped += 1
                continue
            targets.append(file_path)

        if not targets:
            continue

        try:
            html = generate_analyze_deck(
                audit.full_results.get("seo", {}),
                audit.full_results.get("speed", {}),
            )
        except Exception as e:
            print(f"--- ERROR: Failed to regenerate deck for {audit.report_id}: {e} ---")
            failed += 1
            continue

        for file_path in targets:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html)
                fixed += 1
            except Exception as e:
                print(f"--- ERROR: Failed to regenerate {file_path}: {e} ---")
                failed += 1

    return {"fixed": fixed, "skipped": skipped, "failed": failed}



@app.get("/audits/{report_id}")
def get_audit(report_id: str, db: Session = Depends(get_db)):
    audit = db.query(Audit).filter(Audit.report_id == report_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return _audit_api_payload(audit, reused=False)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
