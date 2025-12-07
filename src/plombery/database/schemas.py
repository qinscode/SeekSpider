from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from plombery.schemas import PipelineRunStatus, TaskRun


class PipelineRunBase(BaseModel):
    pipeline_id: str
    trigger_id: str
    status: PipelineRunStatus
    start_time: datetime
    tasks_run: List[TaskRun] = Field(default_factory=list)
    input_params: Optional[dict] = None
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class PipelineRun(PipelineRunBase):
    id: int
    duration: float


class PipelineRunCreate(PipelineRunBase):
    pass


class ApiTokenBase(BaseModel):
    name: str

    class Config:
        from_attributes = True


class ApiToken(ApiTokenBase):
    id: int
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_active: bool


class ApiTokenCreate(ApiTokenBase):
    pass


class ApiTokenWithSecret(ApiToken):
    token: str
