import json
from pathlib import Path

import httpx

from app.core.config import get_settings

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts" / "judge"


def get_judge_prompt(prompt_name: str, **kwargs) -> str:
    prompt_path = _PROMPTS_DIR / prompt_name
    if not prompt_path.exists():
        available = [str(p.relative_to(_PROMPTS_DIR)) for p in sorted(_PROMPTS_DIR.rglob("*")) if p.is_file()]
        raise FileNotFoundError(
            f"Judge prompt file not found: {prompt_path}. "
            f"Expected one of: {available}"
        )
    raw = prompt_path.read_text(encoding="utf-8")
    try:
        return raw.format(**kwargs)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"Missing prompt variable '{missing}' for judge prompt '{prompt_name}'") from exc


def judge_route(expected_route: str, actual_route: str) -> float:
    return 1.0 if expected_route == actual_route else 0.0


async def judge_case_overall(
    *,
    subject: str,
    body: str,
    expected_route: str,
    expect_hitl: bool,
    actual_route: str,
    system_snapshot: dict,
) -> float:
    baseline = judge_route(expected_route, actual_route)
    settings = get_settings()
    if not settings.openai_api_key:
        return baseline

    case_json = json.dumps(
        {
            "email_subject": subject,
            "email_body": body,
            "golden": {"expected_route": expected_route, "expect_hitl": expect_hitl},
            "actual_route": actual_route,
            "system_snapshot": system_snapshot,
        },
        ensure_ascii=False,
    )[:24000]
    system_prompt = get_judge_prompt("system.txt")
    user_prompt = get_judge_prompt("user.txt", case_json=case_json)
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
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)

    score = parsed.get("overall_score", baseline)
    try:
        return max(0.0, min(1.0, float(score)))
    except (TypeError, ValueError):
        return baseline
