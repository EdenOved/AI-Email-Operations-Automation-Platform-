from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import EvalRun, EvalRunCaseResult
from app.evals.dataset import build_eval_dataset
from app.evals.judge import judge_case_overall
from app.process.llm import classify_and_extract
from app.process.routing_policy import apply_confidence_policy, route_from_classification
from app.utils import new_id


async def run_eval(session: AsyncSession, judge_enabled: bool = False) -> EvalRun:
    run = EvalRun(
        id=new_id("evr"),
        status="running",
        model=get_settings().openai_model if get_settings().openai_api_key else "heuristic",
        judge_model=get_settings().openai_model if judge_enabled and get_settings().openai_api_key else None,
    )
    session.add(run)
    await session.commit()
    cases = await build_eval_dataset(session)
    passes = 0
    judge_scores: list[float] = []
    for case in cases:
        parsed = await classify_and_extract(case["subject"], case["body"])
        routing = apply_confidence_policy(parsed, route_from_classification(parsed), get_settings())
        actual_route = routing.route
        correct = actual_route == case["expected_route"]
        if correct:
            passes += 1
        if judge_enabled:
            judge_score = await judge_case_overall(
                subject=case["subject"],
                body=case["body"],
                expected_route=case["expected_route"],
                expect_hitl=case["expect_hitl"],
                actual_route=actual_route,
                system_snapshot={
                    "classification": parsed.classification.model_dump(),
                    "extraction": parsed.extraction.model_dump(),
                    "routing": routing.model_dump(),
                },
            )
            judge_scores.append(judge_score)
        else:
            judge_score = None
        session.add(
            EvalRunCaseResult(
                id=new_id("evc"),
                run_id=run.id,
                case_id=case["id"],
                case_name=case["name"],
                expected_route=case["expected_route"],
                actual_route=actual_route,
                expected_hitl=case["expect_hitl"],
                actual_hitl=actual_route == "hitl",
                route_correct=correct,
                confidence=parsed.classification.routing_confidence,
                reason=parsed.classification.route_reason_summary,
                judge_overall=judge_score,
            )
        )
    total = len(cases)
    run.status = "completed"
    run.case_total = total
    run.route_pass = passes
    run.route_fail = max(0, total - passes)
    run.pass_rate = (passes / total) if total else 0.0
    run.judge_avg_overall = (sum(judge_scores) / len(judge_scores)) if judge_scores else None
    await session.commit()
    return run
