import base64
from email.utils import parsedate_to_datetime

import httpx

from app.core.config import get_settings


def decode_gmail_body(payload: dict) -> str:
    parts = payload.get("parts") or []
    for part in parts:
        body_data = (part.get("body") or {}).get("data")
        mime = part.get("mimeType") or ""
        if body_data and mime in ("text/plain", "text/html"):
            raw = base64.urlsafe_b64decode(body_data + "===")
            return raw.decode("utf-8", errors="replace")
    body_data = (payload.get("body") or {}).get("data")
    if body_data:
        raw = base64.urlsafe_b64decode(body_data + "===")
        return raw.decode("utf-8", errors="replace")
    return ""


async def gmail_access_token() -> str:
    s = get_settings()
    if not (s.gmail_client_id and s.gmail_client_secret and s.gmail_refresh_token):
        raise RuntimeError("Gmail sync requires GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": s.gmail_client_id,
                "client_secret": s.gmail_client_secret,
                "refresh_token": s.gmail_refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def gmail_list_message_ids(max_results: int, query: str) -> list[str]:
    s = get_settings()
    token = await gmail_access_token()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/{s.gmail_user_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"maxResults": max_results, "q": query},
        )
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("messages", [])]


async def gmail_get_message(message_id: str) -> dict:
    s = get_settings()
    token = await gmail_access_token()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/{s.gmail_user_id}/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "full"},
        )
        resp.raise_for_status()
        return resp.json()


def normalize_gmail_message(data: dict) -> dict:
    payload = data.get("payload") or {}
    headers = {h.get("name", "").lower(): h.get("value", "") for h in payload.get("headers", [])}
    date_header = headers.get("date")
    received_at = None
    if date_header:
        try:
            received_at = parsedate_to_datetime(date_header)
        except Exception:
            received_at = None
    internal_ts = None
    try:
        if data.get("internalDate") is not None:
            internal_ts = int(data["internalDate"])
    except Exception:
        internal_ts = None
    return {
        "provider_message_id": data["id"],
        "thread_id": data.get("threadId"),
        "rfc_message_id": headers.get("message-id"),
        "in_reply_to": headers.get("in-reply-to"),
        "references": headers.get("references"),
        "from_address": headers.get("from", ""),
        "to_addresses": headers.get("to"),
        "subject": headers.get("subject"),
        "body_text": decode_gmail_body(payload),
        "received_at": received_at,
        "internal_ts_ms": internal_ts,
    }
