from app.core.config import Settings
from app.schemas.llm import RoutingResult, StructuredResult


def route_from_classification(result: StructuredResult) -> RoutingResult:
    cls = result.classification
    if cls.primary_intent == "crm_focused":
        return RoutingResult(route="crm_only", rationale="intent=crm_focused")
    if cls.primary_intent == "engineering_focused":
        return RoutingResult(route="jira_only", rationale="intent=engineering_focused")
    if cls.primary_intent == "crm_and_engineering":
        return RoutingResult(route="both", rationale="intent=crm_and_engineering")
    if cls.primary_intent == "no_action":
        return RoutingResult(route="noop", rationale="intent=no_action")
    return RoutingResult(route="hitl", requires_hitl=True, rationale="intent=unclear")


def apply_confidence_policy(result: StructuredResult, routing: RoutingResult, settings: Settings) -> RoutingResult:
    cls = result.classification
    if routing.route in ("noop", "hitl") or routing.requires_hitl:
        return routing
    threshold = settings.routing_hitl_confidence_threshold
    high_sensitivity_threshold = max(0.85, min(0.97, threshold + 0.2))
    if cls.sensitivity == "high" and cls.routing_confidence < high_sensitivity_threshold:
        return RoutingResult(
            route="hitl",
            requires_hitl=True,
            rationale=f"high_sensitivity_low_confidence:{cls.routing_confidence:.2f}",
        )
    if cls.routing_confidence < threshold:
        return RoutingResult(
            route="hitl",
            requires_hitl=True,
            rationale=f"low_confidence:{cls.routing_confidence:.2f}",
        )
    # Model review hint alone should not force HITL when confidence is already strong.
    if cls.human_review_recommended and cls.routing_confidence < min(0.95, threshold + 0.1):
        return RoutingResult(route="hitl", requires_hitl=True, rationale="model_requested_review")
    return routing
