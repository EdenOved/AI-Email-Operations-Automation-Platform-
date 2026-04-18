import httpx

from app.core.config import get_settings


def _adf_text_document(text: str) -> dict:
    value = (text or "").strip()
    if not value:
        value = "No details provided."
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": value}],
            }
        ],
    }


async def execute(payload: dict, action: str) -> tuple[str, int, str, str | None]:
    s = get_settings()
    if not (s.jira_base_url and s.jira_email and s.jira_api_token):
        return ("skipped", 0, "JIRA credentials missing", None)
    auth = (s.jira_email, s.jira_api_token)
    base = s.jira_base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=20, auth=auth) as client:
        if action == "comment" and payload.get("target_issue_key"):
            issue_key = str(payload["target_issue_key"])
            resp = await client.post(
                f"{base}/rest/api/3/issue/{issue_key}/comment",
                json={"body": _adf_text_document(str(payload.get("description") or payload.get("summary") or ""))},
            )
            return ("succeeded" if resp.status_code < 300 else "failed", resp.status_code, resp.text[:1000], issue_key)
        if action == "update" and payload.get("target_issue_key"):
            issue_key = str(payload["target_issue_key"])
            resp = await client.put(
                f"{base}/rest/api/3/issue/{issue_key}",
                json={"fields": {"description": _adf_text_document(str(payload.get("description") or ""))}},
            )
            return ("succeeded" if resp.status_code < 300 else "failed", resp.status_code, resp.text[:1000], issue_key)
        issue_payload = {
            "fields": {
                "project": {"key": s.jira_project_key},
                "summary": payload.get("summary") or "Email automation case",
                "description": _adf_text_document(str(payload.get("description") or "")),
                "issuetype": {"name": s.jira_issue_type},
            }
        }
        resp = await client.post(f"{base}/rest/api/3/issue", json=issue_payload)
        issue_key = None
        try:
            if resp.status_code < 300:
                issue_key = str(resp.json().get("key"))
        except Exception:
            issue_key = None
        return ("succeeded" if resp.status_code < 300 else "failed", resp.status_code, resp.text[:1000], issue_key)
