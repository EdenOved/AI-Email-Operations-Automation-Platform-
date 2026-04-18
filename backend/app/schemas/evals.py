from pydantic import BaseModel


class EvalRunCreatePayload(BaseModel):
    judge_enabled: bool = False
