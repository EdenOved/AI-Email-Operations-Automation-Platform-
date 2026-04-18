from app.core.config import Settings
from app.process.routing_policy import apply_confidence_policy, route_from_classification
from app.schemas.llm import Classification, Extraction, StructuredResult


def _result(intent: str, confidence: float, human_review: bool = False) -> StructuredResult:
    return StructuredResult(
        classification=Classification(
            primary_intent=intent,
            sensitivity="normal",
            routing_confidence=confidence,
            route_reason_summary="test",
            uncertainty_indicators=[],
            human_review_recommended=human_review,
            content_category="actionable",
        ),
        extraction=Extraction(),
    )


def test_route_intent_mapping():
    assert route_from_classification(_result("crm_focused", 0.9)).route == "crm_only"
    assert route_from_classification(_result("engineering_focused", 0.9)).route == "jira_only"
    assert route_from_classification(_result("crm_and_engineering", 0.9)).route == "both"
    assert route_from_classification(_result("no_action", 0.9)).route == "noop"


def test_low_confidence_escalates_hitl():
    settings = Settings(ROUTING_HITL_CONFIDENCE_THRESHOLD=0.48)
    result = _result("crm_focused", 0.2)
    routed = apply_confidence_policy(result, route_from_classification(result), settings)
    assert routed.route == "hitl"
    assert routed.requires_hitl is True
