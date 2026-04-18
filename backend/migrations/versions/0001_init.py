"""init

Revision ID: 0001_init
Revises:
Create Date: 2026-04-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _id_cols():
    return [
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "tenants",
        *_id_cols(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("settings_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "emails",
        *_id_cols(),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("rfc_message_id", sa.String(length=255), nullable=True),
        sa.Column("in_reply_to", sa.String(length=255), nullable=True),
        sa.Column("references", sa.Text(), nullable=True),
        sa.Column("from_address", sa.String(length=320), nullable=False),
        sa.Column("to_addresses", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_internal_ts_ms", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
    )
    op.create_index("ix_emails_tenant_id", "emails", ["tenant_id"])
    op.create_index("ix_emails_provider_message_id", "emails", ["provider_message_id"], unique=True)
    op.create_index("ix_emails_provider_internal_ts_ms", "emails", ["provider_internal_ts_ms"])
    op.create_index("ix_emails_status", "emails", ["status"])

    op.create_table(
        "extraction_runs",
        *_id_cols(),
        sa.Column("email_id", sa.String(), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("parsed_json", sa.JSON(), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_extraction_runs_email_id", "extraction_runs", ["email_id"])

    op.create_table(
        "routing_decisions",
        *_id_cols(),
        sa.Column("email_id", sa.String(), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("extraction_run_id", sa.String(), sa.ForeignKey("extraction_runs.id"), nullable=False),
        sa.Column("route", sa.String(length=30), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("requires_hitl", sa.Boolean(), nullable=False),
        sa.Column("decision_confidence", sa.Float(), nullable=True),
        sa.Column("route_reason_summary", sa.String(length=255), nullable=True),
        sa.Column("uncertainty_indicators_json", sa.JSON(), nullable=True),
        sa.Column("human_review_recommended", sa.Boolean(), nullable=False),
        sa.Column("content_category", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_routing_decisions_email_id", "routing_decisions", ["email_id"])
    op.create_index("ix_routing_decisions_route", "routing_decisions", ["route"])

    op.create_table(
        "approval_requests",
        *_id_cols(),
        sa.Column("email_id", sa.String(), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("proposed_route", sa.String(length=30), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_approval_requests_email_id", "approval_requests", ["email_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])

    op.create_table(
        "human_reviews",
        *_id_cols(),
        sa.Column("approval_request_id", sa.String(), sa.ForeignKey("approval_requests.id"), nullable=False),
        sa.Column("reviewer", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("override_route", sa.String(length=30), nullable=True),
    )
    op.create_index("ix_human_reviews_approval_request_id", "human_reviews", ["approval_request_id"])

    op.create_table(
        "integration_jobs",
        *_id_cols(),
        sa.Column("email_id", sa.String(), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("routing_decision_id", sa.String(), sa.ForeignKey("routing_decisions.id"), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_integration_jobs_email_id", "integration_jobs", ["email_id"])
    op.create_index("ix_integration_jobs_provider", "integration_jobs", ["provider"])
    op.create_index("ix_integration_jobs_status", "integration_jobs", ["status"])

    op.create_table(
        "integration_attempts",
        *_id_cols(),
        sa.Column("job_id", sa.String(), sa.ForeignKey("integration_jobs.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_integration_attempts_job_id", "integration_attempts", ["job_id"])

    op.create_table(
        "email_events",
        *_id_cols(),
        sa.Column("email_id", sa.String(), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("detail_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_email_events_email_id", "email_events", ["email_id"])
    op.create_index("ix_email_events_event_type", "email_events", ["event_type"])

    op.create_table(
        "audit_logs",
        *_id_cols(),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("email_id", sa.String(), sa.ForeignKey("emails.id"), nullable=True),
        sa.Column("actor", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("detail_json", sa.JSON(), nullable=True),
    )

    op.create_table(
        "golden_case_candidates",
        *_id_cols(),
        sa.Column("email_id", sa.String(), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("case_name", sa.String(length=500), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("expected_route", sa.String(length=30), nullable=False),
        sa.Column("expect_hitl", sa.Boolean(), nullable=False),
        sa.Column("source_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_golden_case_candidates_email_id", "golden_case_candidates", ["email_id"], unique=True)

    op.create_table(
        "eval_runs",
        *_id_cols(),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("judge_model", sa.String(length=100), nullable=True),
        sa.Column("pass_rate", sa.Float(), nullable=True),
        sa.Column("case_total", sa.Integer(), nullable=True),
        sa.Column("route_pass", sa.Integer(), nullable=True),
        sa.Column("route_fail", sa.Integer(), nullable=True),
        sa.Column("judge_avg_overall", sa.Float(), nullable=True),
    )

    op.create_table(
        "eval_run_case_results",
        *_id_cols(),
        sa.Column("run_id", sa.String(), sa.ForeignKey("eval_runs.id"), nullable=False),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("case_name", sa.String(length=500), nullable=False),
        sa.Column("expected_route", sa.String(length=30), nullable=False),
        sa.Column("actual_route", sa.String(length=30), nullable=False),
        sa.Column("expected_hitl", sa.Boolean(), nullable=False),
        sa.Column("actual_hitl", sa.Boolean(), nullable=False),
        sa.Column("route_correct", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("judge_overall", sa.Float(), nullable=True),
    )
    op.create_index("ix_eval_run_case_results_run_id", "eval_run_case_results", ["run_id"])
    op.create_index("ix_eval_run_case_results_case_id", "eval_run_case_results", ["case_id"])


def downgrade() -> None:
    for table in [
        "eval_run_case_results",
        "eval_runs",
        "golden_case_candidates",
        "audit_logs",
        "email_events",
        "integration_attempts",
        "integration_jobs",
        "human_reviews",
        "approval_requests",
        "routing_decisions",
        "extraction_runs",
        "emails",
        "tenants",
    ]:
        op.drop_table(table)
