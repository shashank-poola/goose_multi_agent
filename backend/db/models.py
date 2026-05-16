import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)     # google | github
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions: Mapped[list["ResearchSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("provider", "provider_id", name="uq_provider_account"),
        Index("ix_users_email", "email"),
    )


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)          # ultra | maverick | remi
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending|running|completed|failed|partial
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    paper_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="sessions")
    report: Mapped[Optional["Report"]] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")
    session_papers: Mapped[list["SessionPaper"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    job: Mapped[Optional["Job"]] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_status", "status"),
        Index("ix_sessions_created_at", "created_at"),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    synthesis: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[list]] = mapped_column(JSON)
    confidence_scores: Mapped[Optional[dict]] = mapped_column(JSON)
    contradictions: Mapped[Optional[list]] = mapped_column(JSON)
    gaps: Mapped[Optional[list]] = mapped_column(JSON)       # Ultra only
    agent_log: Mapped[Optional[list]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["ResearchSession"] = relationship(back_populates="report")


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)     # sha256 hex — Redis cache key
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    authors: Mapped[Optional[list]] = mapped_column(JSON)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), nullable=False)       # exa_search | exa_similar
    qdrant_id: Mapped[Optional[str]] = mapped_column(String(36))          # vector point ID in Qdrant
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session_papers: Mapped[list["SessionPaper"]] = relationship(back_populates="paper", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_papers_url_hash"),
        Index("ix_papers_url_hash", "url_hash"),
        Index("ix_papers_year", "year"),
    )


class SessionPaper(Base):
    __tablename__ = "session_papers"

    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), primary_key=True)
    paper_id: Mapped[str] = mapped_column(String(36), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float)
    primitives: Mapped[Optional[dict]] = mapped_column(JSON)   # classifier output (Ultra/Maverick)
    claims: Mapped[Optional[list]] = mapped_column(JSON)        # decompose output

    session: Mapped["ResearchSession"] = relationship(back_populates="session_papers")
    paper: Mapped["Paper"] = relationship(back_populates="session_papers")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    arq_job_id: Mapped[Optional[str]] = mapped_column(String(255))        # arq job ID for status polling
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")  # queued|processing|done|failed
    worker_id: Mapped[Optional[str]] = mapped_column(String(255))
    error: Mapped[Optional[str]] = mapped_column(Text)
    enqueued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    session: Mapped["ResearchSession"] = relationship(back_populates="job")

    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_session_id", "session_id"),
    )
