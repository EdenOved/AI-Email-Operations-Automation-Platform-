from datetime import date, datetime

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ApprovalRequest, Email, EvalRun, ExtractionRun, IntegrationAttempt, IntegrationJob, RoutingDecision


def _route_from_primary_intent(intent: str | None) -> str | None:
    mapping = {
        "crm_focused": "crm_only",
        "engineering_focused": "jira_only",
        "crm_and_engineering": "both",
        "no_action": "noop",
        "unclear": "hitl",
    }
    return mapping.get(intent or "")


def _approval_snapshot_route_confidence(approval: ApprovalRequest | None) -> tuple[str | None, float | None]:
    if not approval or not approval.snapshot_json:
        return (None, None)
    parsed = (approval.snapshot_json.get("parsed") or {}) if isinstance(approval.snapshot_json, dict) else {}
    classification = parsed.get("classification") or {}
    route = _route_from_primary_intent(classification.get("primary_intent"))
    confidence = classification.get("routing_confidence")
    try:
        confidence_value = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence_value = None
    return (route, confidence_value)


async def get_case_detail(session: AsyncSession, email_id: str) -> dict | None:
    email = await session.get(Email, email_id)
    if email is None:
        return None
    extraction = (
        await session.execute(select(ExtractionRun).where(ExtractionRun.email_id == email_id).order_by(desc(ExtractionRun.created_at)))
    ).scalar_one_or_none()
    routing = (
        await session.execute(select(RoutingDecision).where(RoutingDecision.email_id == email_id).order_by(desc(RoutingDecision.created_at)))
    ).scalar_one_or_none()
    approval = (
        await session.execute(select(ApprovalRequest).where(ApprovalRequest.email_id == email_id).order_by(desc(ApprovalRequest.created_at)))
    ).scalar_one_or_none()
    jobs = list(
        (await session.execute(select(IntegrationJob).where(IntegrationJob.email_id == email_id).order_by(IntegrationJob.created_at))).scalars().all()
    )
    attempts = list(
        (
            await session.execute(
                select(IntegrationAttempt, IntegrationJob.provider)
                .join(IntegrationJob, IntegrationJob.id == IntegrationAttempt.job_id)
                .where(IntegrationJob.email_id == email_id)
                .order_by(desc(IntegrationAttempt.created_at))
            )
        ).all()
    )
    return {
        "email": {
            "id": email.id,
            "subject": email.subject,
            "from_address": email.from_address,
            "body_text": email.body_text,
            "status": email.status,
            "thread_id": email.thread_id,
            "in_reply_to": email.in_reply_to,
            "references": email.references,
            "received_at": email.received_at.isoformat() if email.received_at else None,
            "updated_at": email.updated_at.isoformat(),
        },
        "extraction": extraction.parsed_json if extraction else None,
        "routing": (
            {
                "route": routing.route,
                "confidence": routing.decision_confidence,
                "reason": routing.route_reason_summary,
                "uncertainty_indicators": routing.uncertainty_indicators_json or [],
                "human_review_recommended": routing.human_review_recommended,
            }
            if routing
            else None
        ),
        "approval": (
            {
                "id": approval.id,
                "status": approval.status,
                "reason": approval.reason,
                "proposed_route": approval.proposed_route,
                "created_at": approval.created_at.isoformat(),
            }
            if approval
            else None
        ),
        "jobs": [
            {
                "id": j.id,
                "provider": j.provider,
                "action": j.action,
                "status": j.status,
                "error_detail": j.error_detail,
                "external_id": j.external_id,
                "updated_at": j.updated_at.isoformat(),
            }
            for j in jobs
        ],
        "attempts": [
            {
                "attempt_id": att.id,
                "provider": provider,
                "status": att.status,
                "response_code": att.response_code,
                "error_detail": att.error_detail,
                "created_at": att.created_at.isoformat(),
            }
            for att, provider in attempts
        ],
    }


async def list_inbox(session: AsyncSession, only_failures: bool = False, only_approvals: bool = False, limit: int = 100) -> dict:
    q = select(Email).order_by(desc(Email.updated_at)).limit(limit)
    if only_failures:
        q = q.where(Email.status.in_(["failed", "partial_failure"]))
    rows = list((await session.execute(q)).scalars().all())
    out: list[dict] = []
    for e in rows:
        approval = (
            await session.execute(select(ApprovalRequest).where(ApprovalRequest.email_id == e.id).order_by(desc(ApprovalRequest.created_at)).limit(1))
        ).scalar_one_or_none()
        if only_approvals and (approval is None or approval.status != "pending"):
            continue
        routing = (
            await session.execute(select(RoutingDecision).where(RoutingDecision.email_id == e.id).order_by(desc(RoutingDecision.created_at)).limit(1))
        ).scalar_one_or_none()
        fallback_route, fallback_confidence = _approval_snapshot_route_confidence(approval)
        out.append(
            {
                "email_id": e.id,
                "subject": e.subject,
                "from_address": e.from_address,
                "status": e.status,
                "route": routing.route if routing else fallback_route,
                "routing_confidence": routing.decision_confidence if routing else fallback_confidence,
                "approval_state": approval.status if approval else None,
                "updated_at": e.updated_at.isoformat(),
            }
        )
    return {"items": out, "count": len(out)}


async def pending_approvals(session: AsyncSession, limit: int = 100) -> list[dict]:
    rows = list(
        (
            await session.execute(
                select(ApprovalRequest, Email)
                .join(Email, Email.id == ApprovalRequest.email_id)
                .where(ApprovalRequest.status == "pending")
                .order_by(desc(ApprovalRequest.created_at))
                .limit(limit)
            )
        ).all()
    )
    return [
        {
            "approval_id": a.id,
            "email_id": e.id,
            "subject": e.subject,
            "from_address": e.from_address,
            "reason": a.reason,
            "proposed_route": a.proposed_route,
            "created_at": a.created_at.isoformat(),
        }
        for a, e in rows
    ]


async def operations_summary(session: AsyncSession) -> dict:
    today = date.today()
    # DB columns are TIMESTAMP WITHOUT TIME ZONE, so use naive datetime bounds.
    day_start = datetime(today.year, today.month, today.day)
    total = (await session.execute(select(func.count(Email.id)).where(Email.created_at >= day_start))).scalar_one()
    processed = (
        await session.execute(select(func.count(Email.id)).where(and_(Email.created_at >= day_start, Email.status == "processed")))
    ).scalar_one()
    failures = (
        await session.execute(select(func.count(Email.id)).where(and_(Email.created_at >= day_start, Email.status.in_(["failed", "partial_failure"]))))
    ).scalar_one()
    pending = (
        await session.execute(select(func.count(ApprovalRequest.id)).where(and_(ApprovalRequest.created_at >= day_start, ApprovalRequest.status == "pending")))
    ).scalar_one()
    route_rows = list(
        (
            await session.execute(
                select(RoutingDecision.route, func.count(RoutingDecision.id))
                .where(RoutingDecision.created_at >= day_start)
                .group_by(RoutingDecision.route)
            )
        ).all()
    )
    route_dist = {r: c for r, c in route_rows}
    job_tot = (await session.execute(select(func.count(IntegrationJob.id)).where(IntegrationJob.created_at >= day_start))).scalar_one()
    job_ok = (
        await session.execute(
            select(func.count(IntegrationJob.id)).where(and_(IntegrationJob.created_at >= day_start, IntegrationJob.status == "succeeded"))
        )
    ).scalar_one()
    run = (
        await session.execute(select(EvalRun).where(EvalRun.status == "completed").order_by(desc(EvalRun.created_at)).limit(1))
    ).scalar_one_or_none()
    automated = processed - (
        await session.execute(select(func.count(func.distinct(ApprovalRequest.email_id))).where(ApprovalRequest.created_at >= day_start))
    ).scalar_one()
    automated = max(0, automated)
    roi_hours = round((automated * get_settings().roi_assumed_minutes_per_auto_case) / 60.0, 2)
    return {
        "emails_total_today": total,
        "emails_processed_today": processed,
        "failure_count": failures,
        "hitl_pending_today": pending,
        "route_distribution": route_dist,
        "integration_success_rate": (job_ok / job_tot) if job_tot else 0.0,
        "business_value": {
            "processed_fully_automated_today": automated,
            "processed_after_human_review_today": max(0, processed - automated),
            "assumed_minutes_saved_per_automated_case": get_settings().roi_assumed_minutes_per_auto_case,
            "estimated_human_hours_saved_today": roi_hours,
            "automation_share_of_processed_today": (automated / processed) if processed else 0.0,
            "notes": "Estimated from processed count without HumanReview touch.",
        },
        "latest_completed_eval_snapshot": (
            {
                "run_id": run.id,
                "pass_rate": run.pass_rate,
                "case_total": run.case_total,
                "route_pass": run.route_pass,
                "route_fail": run.route_fail,
                "judge_avg_overall": run.judge_avg_overall,
            }
            if run
            else None
        ),
    }


async def integration_status(live: bool = False) -> dict:
    s = get_settings()
    hub_cfg = bool(s.hubspot_access_token)
    jira_cfg = bool(s.jira_base_url and s.jira_email and s.jira_api_token)
    hub = {"configured": hub_cfg, "checked_live": live, "live_ok": hub_cfg if live else None, "detail": "configured" if hub_cfg else "missing token"}
    jira = {
        "configured": jira_cfg,
        "checked_live": live,
        "live_ok": jira_cfg if live else None,
        "detail": "configured" if jira_cfg else "missing credentials",
    }
    return {"hubspot": hub, "jira": jira}
