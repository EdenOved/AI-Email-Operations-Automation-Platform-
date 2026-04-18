import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Email
from app.db.repos.emails import get_latest_in_thread
from app.db.repos.jobs import latest_success_for_provider

_ACK_ONLY_RE = re.compile(r"^\s*(thanks|thank you|noted|sgtm|got it|received|תודה|התקבל)\W*$", re.I)
_ACTION_WORD_RE = re.compile(r"\b(fix|investigate|update|rollback|urgent|error|incident|issue|api|bug|price|quote|demo)\b", re.I)


def is_ack_only_followup(text: str | None) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if len(t) > 60:
        return False
    if _ACTION_WORD_RE.search(t):
        return False
    return bool(_ACK_ONLY_RE.match(t))


@dataclass(slots=True)
class ThreadContext:
    is_reply_like: bool
    parent_email_id: str | None
    parent_hubspot_ticket_id: str | None
    parent_jira_issue_key: str | None
    ignore_as_ack: bool
    rationale: str | None


async def build_thread_context(session: AsyncSession, email: Email) -> ThreadContext:
    is_reply_like = bool(email.in_reply_to) or (email.subject or "").lower().startswith("re:")
    if not email.thread_id:
        return ThreadContext(
            is_reply_like=is_reply_like,
            parent_email_id=None,
            parent_hubspot_ticket_id=None,
            parent_jira_issue_key=None,
            ignore_as_ack=is_reply_like and is_ack_only_followup(email.body_text),
            rationale="no_thread_id",
        )
    parent = await get_latest_in_thread(session, email.tenant_id, email.thread_id, email.id)
    if parent is None:
        return ThreadContext(
            is_reply_like=is_reply_like,
            parent_email_id=None,
            parent_hubspot_ticket_id=None,
            parent_jira_issue_key=None,
            ignore_as_ack=is_reply_like and is_ack_only_followup(email.body_text),
            rationale="thread_no_parent",
        )
    parent_hubspot_job = await latest_success_for_provider(session, parent.id, "hubspot")
    parent_jira_job = await latest_success_for_provider(session, parent.id, "jira")
    return ThreadContext(
        is_reply_like=is_reply_like,
        parent_email_id=parent.id,
        parent_hubspot_ticket_id=parent_hubspot_job.external_id if parent_hubspot_job else None,
        parent_jira_issue_key=parent_jira_job.external_id if parent_jira_job else None,
        ignore_as_ack=is_reply_like and is_ack_only_followup(email.body_text),
        rationale="thread_parent_found",
    )
