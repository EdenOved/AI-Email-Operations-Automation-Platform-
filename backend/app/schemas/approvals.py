from pydantic import BaseModel


class PromoteHitlPayload(BaseModel):
    email_id: str
