import httpx
import json

from app.core.config import get_settings


async def _resolve_default_ticket_stage(client: httpx.AsyncClient, headers: dict) -> tuple[str | None, str | None]:
    try:
        resp = await client.get("https://api.hubapi.com/crm/v3/pipelines/tickets", headers=headers)
        if resp.status_code >= 300:
            return (None, None)
        data = resp.json()
        pipelines = data.get("results") or []
        if not pipelines:
            return (None, None)
        pipeline = pipelines[0]
        pipeline_id = pipeline.get("id")
        stages = pipeline.get("stages") or []
        if not stages:
            return (pipeline_id, None)
        stage_id = stages[0].get("id")
        return (pipeline_id, stage_id)
    except Exception:
        return (None, None)


def _extract_invalid_property_names(error_text: str) -> list[str]:
    names: list[str] = []
    try:
        payload = json.loads(error_text)
        for err in payload.get("errors") or []:
            ctx = err.get("context") or {}
            prop_names = ctx.get("propertyName") or []
            for prop in prop_names:
                if prop:
                    names.append(str(prop))
        message = str(payload.get("message") or "")
    except Exception:
        message = error_text or ""
    marker = 'Property "'
    idx = 0
    while True:
        start = message.find(marker, idx)
        if start == -1:
            break
        start += len(marker)
        end = message.find('"', start)
        if end == -1:
            break
        names.append(message[start:end])
        idx = end + 1
    return list(dict.fromkeys(names))


async def execute(payload: dict, action: str) -> tuple[str, int, str, str | None]:
    s = get_settings()
    if not s.hubspot_access_token:
        return ("skipped", 0, "HUBSPOT_ACCESS_TOKEN missing", None)
    headers = {"Authorization": f"Bearer {s.hubspot_access_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        if action in ("update", "comment") and payload.get("target_ticket_id"):
            ticket_id = str(payload["target_ticket_id"])
            append = str(payload.get("content") or payload.get("subject") or "")
            resp = await client.patch(
                f"https://api.hubapi.com/crm/v3/objects/tickets/{ticket_id}",
                headers=headers,
                json={"properties": {"content": append[:65535]}},
            )
            return (
                "succeeded" if resp.status_code < 300 else "failed",
                resp.status_code,
                resp.text[:1000],
                ticket_id if resp.status_code < 300 else None,
            )
        retry_payload = dict(payload)
        resp = await client.post(
            "https://api.hubapi.com/crm/v3/objects/tickets",
            headers=headers,
            json={"properties": retry_payload},
        )
        for _ in range(3):
            retried = False
            if resp.status_code == 400 and "hs_pipeline_stage" in resp.text and action == "create":
                pipeline_id, stage_id = await _resolve_default_ticket_stage(client, headers)
                if pipeline_id and "hs_pipeline" not in retry_payload:
                    retry_payload["hs_pipeline"] = pipeline_id
                    retried = True
                if stage_id and "hs_pipeline_stage" not in retry_payload:
                    retry_payload["hs_pipeline_stage"] = stage_id
                    retried = True
            if resp.status_code == 400 and "PROPERTY_DOESNT_EXIST" in resp.text and action == "create":
                for invalid_prop in _extract_invalid_property_names(resp.text):
                    if invalid_prop in retry_payload:
                        retry_payload.pop(invalid_prop, None)
                        retried = True
            if not retried:
                break
            resp = await client.post(
                "https://api.hubapi.com/crm/v3/objects/tickets",
                headers=headers,
                json={"properties": retry_payload},
            )
        external_id = None
        try:
            if resp.status_code < 300:
                external_id = str(resp.json().get("id"))
        except Exception:
            external_id = None
        return ("succeeded" if resp.status_code < 300 else "failed", resp.status_code, resp.text[:1000], external_id)
