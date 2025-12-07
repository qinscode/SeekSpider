from typing import List, Optional

from sqlalchemy import Column, Integer, String, Boolean

from plombery.database.base import Base
from plombery.database.type_helpers import AwareDateTime, PydanticType
from plombery.schemas import TaskRun


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(String, index=True)
    trigger_id = Column(String)
    status = Column(String)
    start_time = Column(AwareDateTime)
    duration = Column(Integer, default=0)
    tasks_run = Column(PydanticType(List[TaskRun]), default=list)
    input_params = Column(PydanticType(Optional[dict]), default=None)
    reason = Column(String, default=None)


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(AwareDateTime, nullable=False)
    last_used_at = Column(AwareDateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
