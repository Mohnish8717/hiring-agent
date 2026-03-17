"""
PostgreSQL ORM models for multi-tenant ATS data.

Tables:
    - tenants          : Organisation-level isolation
    - candidates       : Per-resume analysis records
    - audit_logs       : Every pipeline action is logged for compliance
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Integer, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=True)
    api_key_hash = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    candidates = relationship("Candidate", back_populates="tenant", lazy="selectin")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    request_id = Column(String(64), unique=True, nullable=False, index=True)
    email_hash = Column(String(128), nullable=True)  # SHA-256 of email — no PII stored

    # Scores
    total_score = Column(Float, default=0.0)
    trust_score = Column(Float, default=0.0)
    skill_match_score = Column(Float, default=0.0)
    ai_generated_probability = Column(Float, default=0.0)
    success_probability = Column(Float, default=0.0)

    # Metadata
    status = Column(String(32), default="pending")  # pending | processing | complete | error
    job_description = Column(Text, nullable=True)
    result_data = Column(JSON, nullable=True)        # Full serialised pipeline output
    contribution_map = Column(JSON, nullable=True)

    # Storage keys (MinIO object keys)
    resume_object_key = Column(String(512), nullable=True)
    report_object_key = Column(String(512), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant", back_populates="candidates")
    audit_logs = relationship("AuditLog", back_populates="candidate", lazy="selectin")

    __table_args__ = (
        Index("ix_candidates_tenant_status", "tenant_id", "status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    agent_name = Column(String(128), nullable=False)
    action = Column(String(255), nullable=False)
    detail = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow)

    candidate = relationship("Candidate", back_populates="audit_logs")
