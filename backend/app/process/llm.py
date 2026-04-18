import json
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.schemas.llm import Classification, Extraction, StructuredResult

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def get_prompt(prompt_name: str, **kwargs) -> str:
    prompt_path = _PROMPTS_DIR / prompt_name
    if not prompt_path.exists():
        available = [str(p.relative_to(_PROMPTS_DIR)) for p in sorted(_PROMPTS_DIR.rglob("*")) if p.is_file()]
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. "
            f"Expected one of: {available}"
        )
    raw = prompt_path.read_text(encoding="utf-8")
    try:
        return raw.format(**kwargs)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"Missing prompt variable '{missing}' for prompt '{prompt_name}'") from exc


def _heuristic_classify(subject: str, body: str) -> StructuredResult:
    text = f"{subject}\n{body}".lower()
    has_sales = any(x in text for x in ["demo", "pricing", "quote", "renewal", "partnership", "sales"])
    has_eng = any(x in text for x in ["bug", "incident", "sev", "outage", "500", "api", "error", "production"])
    high = any(x in text for x in ["legal", "wire transfer", "bank account", "payment details"])

    if "unsubscribe" in text or "newsletter" in text or "no action required" in text:
        intent = "no_action"
        route = "newsletter-like noise"
        conf = 0.9
    elif has_sales and has_eng:
        intent = "crm_and_engineering"
        route = "commercial ask + engineering execution"
        conf = 0.75
    elif has_eng:
        intent = "engineering_focused"
        route = "technical execution request"
        conf = 0.82
    elif has_sales:
        intent = "crm_focused"
        route = "commercial/customer workflow"
        conf = 0.84
    else:
        intent = "unclear"
        route = "insufficient or ambiguous intent signal"
        conf = 0.33

    return StructuredResult(
        classification=Classification(
            primary_intent=intent,
            sensitivity="high" if high else "normal",
            routing_confidence=conf,
            route_reason_summary=route,
            uncertainty_indicators=[] if conf > 0.6 else ["ambiguous_intent"],
            human_review_recommended=conf < 0.5,
            content_category="notification_noise" if intent == "no_action" else "actionable",
        ),
        extraction=Extraction(
            account_name=None,
            contact_email=None,
            jira_summary=subject[:250] if subject else None,
            jira_description=body[:4000] if body else None,
            suggested_priority="high" if has_eng and "sev" in text else "medium",
            suggested_action="comment" if "re:" in (subject or "").lower() else "create",
        ),
    )


async def classify_and_extract(subject: str, body: str) -> StructuredResult:
    settings = get_settings()
    if not settings.openai_api_key:
        return _heuristic_classify(subject, body)

    subject_for_llm = (subject or "").strip()
    body_for_llm = (body or "")[:12000]
    system_prompt = get_prompt("classify_extract/system.txt")
    user_prompt = get_prompt("classify_extract/user.txt", subject=subject_for_llm, body=body_for_llm)
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return StructuredResult.model_validate(json.loads(content))
