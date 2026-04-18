from pydantic import BaseModel


class ApprovalDecisionPayload(BaseModel):
    action: str
    reviewer: str | None = "operator"
    notes: str | None = None
    override_route: str | None = None
