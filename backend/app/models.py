from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, Float, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    # Module access — toggled on Access (superadmin / access-admin users)
    can_analyze = Column(Boolean, default=True, nullable=False)
    can_snapshot = Column(Boolean, default=True, nullable=False)
    can_bulk = Column(Boolean, default=True, nullable=False)
    can_quick_audit = Column(Boolean, default=True, nullable=False)
    can_access = Column(Boolean, default=False, nullable=False)
    # Lifetime DataForSEO spend attributed to this operator (USD)
    credit_used_usd = Column(Float, default=0.0, nullable=False)
    # Monthly quotas (UTC calendar month). None = unlimited.
    monthly_audit_limit = Column(Integer, nullable=True)
    monthly_quick_audit_limit = Column(Integer, nullable=True)
    monthly_snapshot_limit = Column(Integer, nullable=True)
    # Legacy lifetime field — kept so old DBs still load; prefer monthly_* above.
    audit_limit = Column(Integer, nullable=True)

    audits = relationship("Audit", back_populates="owner")
    jobs = relationship("BulkJob", back_populates="owner")
    snapshots = relationship("Snapshot", back_populates="owner")

class Audit(Base):
    __tablename__ = "audits"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    url = Column(String, nullable=False)
    seo_score = Column(String, default="N/A")
    speed_score = Column(String, default="N/A")
    report_id = Column(String, unique=True, index=True)
    full_results = Column(JSONB, nullable=True)
    api_cost_usd = Column(Float, default=0.0, nullable=False)
    usage_log = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="audits")

class BulkJob(Base):
    __tablename__ = "bulk_jobs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    input_filename = Column(String, nullable=False)
    output_filename = Column(String, nullable=True)
    status = Column(String, default="pending")
    total_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="jobs")


class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prospect_url = Column(String, nullable=False)
    prospect_domain = Column(String, nullable=False)
    competitor_url = Column(String, nullable=False)
    competitor_domain = Column(String, nullable=False)
    competitor_mode = Column(String, default="auto")  # auto | manual
    competitor_urls = Column(JSONB, nullable=True)  # up to 3 domains when manual
    location_code = Column(Integer, default=2840)
    language_code = Column(String, default="en")
    status = Column(String, default="pending")
    progress = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    payload = Column(JSONB, nullable=True)
    top_fixes = Column(JSONB, nullable=True)
    booking_url = Column(String, nullable=True)
    thin_data = Column(Boolean, default=False)
    api_cost_usd = Column(Float, default=0)
    usage_log = Column(JSONB, nullable=True)
    pptx_filename = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="snapshots")
