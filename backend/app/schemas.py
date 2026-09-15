from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from enum import Enum

class ReportType(str, Enum):
    SEO = "seo"
    SPEED = "speed"
    BOTH = "both"
    QUICK = "quick"

class AnalysisRequest(BaseModel):
    url: str
    report_type: ReportType = ReportType.BOTH
    force: bool = False
    """If true, always run a fresh audit even when this domain was audited before."""

class AnalysisResponse(BaseModel):
    id: str
    url: str
    status: str
    seo_report_url: Optional[str] = None
    speed_report_url: Optional[str] = None
    seo_pdf_url: Optional[str] = None
    speed_pdf_url: Optional[str] = None


class SnapshotCreateRequest(BaseModel):
    prospect_url: str
    competitor_url: Optional[str] = None
    """Legacy single competitor; prefer competitor_urls + competitor_mode."""
    competitor_mode: str = "auto"
    """auto = DataForSEO Labs peers (filtered); manual = operator-supplied domains."""
    competitor_urls: Optional[List[str]] = None
    """Up to 3 competitor URLs/domains when competitor_mode is manual."""
    location_code: int = 2840
    language_code: str = "en"
    force: bool = False
    """If true, always pull a fresh snapshot even when this domain was snapshotted before."""


class ProjectionRowEdit(BaseModel):
    key: str
    target: str


class SnapshotUpdateRequest(BaseModel):
    top_fixes: Optional[List[str]] = None
    booking_url: Optional[str] = None
    projection_rows: Optional[List[ProjectionRowEdit]] = None


class SnapshotApproveRequest(BaseModel):
    top_fixes: Optional[List[str]] = None
    booking_url: Optional[str] = None
    projection_rows: Optional[List[ProjectionRowEdit]] = None


class UserPermissionsUpdate(BaseModel):
    can_analyze: bool
    can_snapshot: bool
    can_bulk: bool
    can_quick_audit: bool = True
    can_access: bool
    display_name: Optional[str] = None
    # Monthly quotas (UTC). None = unlimited; 0 = blocked for the month.
    monthly_audit_limit: Optional[int] = None
    monthly_quick_audit_limit: Optional[int] = None
    monthly_snapshot_limit: Optional[int] = None


class ProfileUpdate(BaseModel):
    """Self-service profile edits. Email is never accepted here."""

    display_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
