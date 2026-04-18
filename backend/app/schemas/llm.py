from pydantic import BaseModel, Field


class Classification(BaseModel):
    primary_intent: str = Field(description="crm_focused|engineering_focused|crm_and_engineering|no_action|unclear")
    sensitivity: str = Field(default="normal")
    routing_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    route_reason_summary: str = Field(default="")
    uncertainty_indicators: list[str] = Field(default_factory=list)
    human_review_recommended: bool = False
    content_category: str = Field(default="actionable")


class Extraction(BaseModel):
    account_name: str | None = None
    contact_email: str | None = None
    jira_summary: str | None = None
    jira_description: str | None = None
    suggested_priority: str = "medium"
    suggested_action: str = "create"


class StructuredResult(BaseModel):
    classification: Classification
    extraction: Extraction


class RoutingResult(BaseModel):
    route: str
    requires_hitl: bool = False
    rationale: str = ""
