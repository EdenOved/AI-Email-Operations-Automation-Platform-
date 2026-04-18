import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repos.evals import list_golden_candidates


def load_builtin_cases() -> list[dict]:
    path = Path(__file__).resolve().parent / "golden_cases.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("cases", [])


async def build_eval_dataset(session: AsyncSession) -> list[dict]:
    db_cases = await list_golden_candidates(session)
    merged = load_builtin_cases()
    for c in db_cases:
        merged.append(
            {
                "id": f"hitl_{c.email_id}",
                "name": c.case_name,
                "subject": c.subject or "",
                "body": c.body or "",
                "expected_route": c.expected_route,
                "expect_hitl": c.expect_hitl,
            }
        )
    return merged
