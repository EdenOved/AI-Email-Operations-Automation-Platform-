from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ApprovalRequest, Email, EmailEvent, ExtractionRun, IntegrationJob, RoutingDecision
from app.process.llm import classify_and_extract
from app.process.routing_policy import apply_confidence_policy, route_from_classification
from app.process.thread_policy import build_thread_context
from app.schemas.llm import RoutingResult, StructuredResult
from app.utils import new_id


def _has_explicit_high_sensitivity_signal(subject: str, body: str) -> bool:
    text = f"{subject}\n{body}".lower()
    signals = [
        "wire transfer",
        "bank account",
        "payment details",
        "change payment method",
        "update payment method",
        "credit card",
        "iban",
        "swift",
        "fraud",
        "credential",
        "password reset",
        "security breach",
        "legal hold",
    ]
    return any(sig in text for sig in signals)


def _normalize_classification_for_policy(parsed: StructuredResult) -> None:
    cls = parsed.classification
    # Keep classifier outputs internally consistent with routing policy.
    if cls.primary_intent == "unclear" and cls.routing_confidence > 0.4:
        cls.routing_confidence = 0.4
        cls.human_review_recommended = True
    if cls.uncertainty_indicators and cls.routing_confidence > 0.75:
        cls.routing_confidence = 0.75
    if cls.human_review_recommended and cls.routing_confidence > 0.92:
        cls.human_review_recommended = False


def resolve_hubspot_action(thread_ctx) -> tuple[str, str | None]:
    if thread_ctx.parent_hubspot_ticket_id:
        return ("comment" if thread_ctx.is_reply_like else "update", thread_ctx.parent_hubspot_ticket_id)
    return ("create", None)


def resolve_jira_action(thread_ctx) -> tuple[str, str | None]:
    if thread_ctx.parent_jira_issue_key:
        return ("comment" if thread_ctx.is_reply_like else "update", thread_ctx.parent_jira_issue_key)
    return ("create", None)


async def create_hitl_approval(
    session: AsyncSession, email: Email, reason: str, route: str, parsed: StructuredResult, routing: RoutingResult
) -> None:
    approval = ApprovalRequest(
        id=new_id("apr"),
        email_id=email.id,
        status="pending",
        reason=reason,
        proposed_route=route,
        snapshot_json={"parsed": parsed.model_dump(), "routing": routing.model_dump()},
    )
    session.add(approval)
    email.status = "awaiting_approval"
    session.add(EmailEvent(id=new_id("evt"), email_id=email.id, event_type="awaiting_approval", detail_json={"reason": reason}))
    await session.commit()


async def plan_integration_jobs(
    session: AsyncSession, email: Email, route: str, run_id: str, parsed: StructuredResult, thread_ctx
) -> RoutingDecision:
    cls = parsed.classification
    decision = RoutingDecision(
        id=new_id("rd"),
        email_id=email.id,
        extraction_run_id=run_id,
        route=route,
        rationale=cls.route_reason_summary,
        requires_hitl=False,
        decision_confidence=cls.routing_confidence,
        route_reason_summary=cls.route_reason_summary,
        uncertainty_indicators_json=cls.uncertainty_indicators,
        human_review_recommended=cls.human_review_recommended,
        content_category=cls.content_category,
    )
    session.add(decision)
    # Ensure FK target exists before planning IntegrationJob rows.
    await session.flush()
    if route in ("crm_only", "both"):
        action, target_ticket_id = resolve_hubspot_action(thread_ctx)
        settings = get_settings()
        payload = {
            "subject": email.subject or "",
            "content": email.body_text or "",
            "source_email_id": email.id,
            "account_name": parsed.extraction.account_name or "",
            "contact_email": parsed.extraction.contact_email or email.from_address,
        }
        if settings.hubspot_pipeline:
            payload["hs_pipeline"] = settings.hubspot_pipeline
        if settings.hubspot_pipeline_stage:
            payload["hs_pipeline_stage"] = settings.hubspot_pipeline_stage
        if target_ticket_id:
            payload["target_ticket_id"] = target_ticket_id
        session.add(
            IntegrationJob(
                id=new_id("job"),
                email_id=email.id,
                routing_decision_id=decision.id,
                provider="hubspot",
                action=action,
                status="planned",
                payload_json=payload,
            )
        )
    if route in ("jira_only", "both"):
        action, target_issue_key = resolve_jira_action(thread_ctx)
        payload = {
            "summary": parsed.extraction.jira_summary or email.subject or "Email case",
            "description": parsed.extraction.jira_description or email.body_text or "",
            "priority": parsed.extraction.suggested_priority,
            "source_email_id": email.id,
        }
        if target_issue_key:
            payload["target_issue_key"] = target_issue_key
        session.add(
            IntegrationJob(
                id=new_id("job"),
                email_id=email.id,
                routing_decision_id=decision.id,
                provider="jira",
                action=action,
                status="planned",
                payload_json=payload,
            )
        )
    email.status = "routed"
    session.add(
        EmailEvent(
            id=new_id("evt"),
            email_id=email.id,
            event_type="routed",
            detail_json={"route": route, "thread_rationale": thread_ctx.rationale},
        )
    )
    await session.commit()
    return decision


async def run_pipeline_for_email(session: AsyncSession, email: Email) -> None:
    email.status = "processing"
    await session.commit()
    parsed = await classify_and_extract(email.subject or "", email.body_text or "")
    if parsed.classification.sensitivity == "high" and not _has_explicit_high_sensitivity_signal(email.subject or "", email.body_text or ""):
        parsed.classification.sensitivity = "normal"
    _normalize_classification_for_policy(parsed)
    run = ExtractionRun(
        id=new_id("ext"),
        email_id=email.id,
        status="succeeded",
        model=get_settings().openai_model if get_settings().openai_api_key else "heuristic",
        parsed_json=parsed.model_dump(),
        error_detail=None,
    )
    session.add(run)
    await session.commit()
    routing = route_from_classification(parsed)
    routing = apply_confidence_policy(parsed, routing, settings=get_settings())
    thread_ctx = await build_thread_context(session, email)
    if thread_ctx.ignore_as_ack and routing.route in ("crm_only", "jira_only", "both"):
        email.status = "processed"
        session.add(
            EmailEvent(
                id=new_id("evt"),
                email_id=email.id,
                event_type="noop_ack_followup",
                detail_json={"rationale": thread_ctx.rationale},
            )
        )
        await session.commit()
        return
    if routing.route == "noop":
        email.status = "processed"
        session.add(EmailEvent(id=new_id("evt"), email_id=email.id, event_type="noop", detail_json={"reason": routing.rationale}))
        await session.commit()
        return
    if routing.route == "hitl" or routing.requires_hitl:
        await create_hitl_approval(session, email, routing.rationale or "hitl_required", "hitl", parsed, routing)
        return
    await plan_integration_jobs(session, email, routing.route, run.id, parsed, thread_ctx)
