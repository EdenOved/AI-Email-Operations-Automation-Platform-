from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Tenant(Base):
    __tablename__ = "tenants"
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    settings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Email(Base):
    __tablename__ = "emails"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30), default="gmail")
    provider_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    rfc_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_address: Mapped[str] = mapped_column(String(320))
    to_addresses: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_internal_ts_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), index=True, default="received")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    email_id: Mapped[str] = mapped_column(ForeignKey("emails.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="succeeded")
    model: Mapped[str] = mapped_column(String(100))
    parsed_json: Mapped[dict] = mapped_column(JSON)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class RoutingDecision(Base):
    __tablename__ = "routing_decisions"
    email_id: Mapped[str] = mapped_column(ForeignKey("emails.id"), index=True)
    extraction_run_id: Mapped[str] = mapped_column(ForeignKey("extraction_runs.id"), index=True)
    route: Mapped[str] = mapped_column(String(30), index=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_hitl: Mapped[bool] = mapped_column(Boolean, default=False)
    decision_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    route_reason_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uncertainty_indicators_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    human_review_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    content_category: Mapped[str | None] = mapped_column(String(50), nullable=True)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    email_id: Mapped[str] = mapped_column(ForeignKey("emails.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    reason: Mapped[str] = mapped_column(Text)
    proposed_route: Mapped[str | None] = mapped_column(String(30), nullable=True)
    snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class HumanReview(Base):
    __tablename__ = "human_reviews"
    approval_request_id: Mapped[str] = mapped_column(ForeignKey("approval_requests.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(120), default="operator")
    action: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_route: Mapped[str | None] = mapped_column(String(30), nullable=True)


class IntegrationJob(Base):
    __tablename__ = "integration_jobs"
    email_id: Mapped[str] = mapped_column(ForeignKey("emails.id"), index=True)
    routing_decision_id: Mapped[str] = mapped_column(ForeignKey("routing_decisions.id"), index=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    action: Mapped[str] = mapped_column(String(20), default="create")
    status: Mapped[str] = mapped_column(String(30), default="planned", index=True)
    payload_json: Mapped[dict] = mapped_column(JSON)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntegrationAttempt(Base):
    __tablename__ = "integration_attempts"
    job_id: Mapped[str] = mapped_column(ForeignKey("integration_jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmailEvent(Base):
    __tablename__ = "email_events"
    email_id: Mapped[str] = mapped_column(ForeignKey("emails.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    email_id: Mapped[str | None] = mapped_column(ForeignKey("emails.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(120))
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class GoldenCaseCandidate(Base):
    __tablename__ = "golden_case_candidates"
    email_id: Mapped[str] = mapped_column(ForeignKey("emails.id"), unique=True, index=True)
    case_name: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_route: Mapped[str] = mapped_column(String(30))
    expect_hitl: Mapped[bool] = mapped_column(Boolean, default=False)
    source_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class EvalRun(Base):
    __tablename__ = "eval_runs"
    status: Mapped[str] = mapped_column(String(30), default="queued")
    model: Mapped[str] = mapped_column(String(100))
    judge_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    case_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    route_pass: Mapped[int | None] = mapped_column(Integer, nullable=True)
    route_fail: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge_avg_overall: Mapped[float | None] = mapped_column(Float, nullable=True)


class EvalRunCaseResult(Base):
    __tablename__ = "eval_run_case_results"
    run_id: Mapped[str] = mapped_column(ForeignKey("eval_runs.id"), index=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    case_name: Mapped[str] = mapped_column(String(500))
    expected_route: Mapped[str] = mapped_column(String(30))
    actual_route: Mapped[str] = mapped_column(String(30))
    expected_hitl: Mapped[bool] = mapped_column(Boolean, default=False)
    actual_hitl: Mapped[bool] = mapped_column(Boolean, default=False)
    route_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
