from typing import List, Optional
from datetime import datetime, timezone

from plombery.schemas import PipelineRunStatus

from .base import SessionLocal
from .schemas import PipelineRunCreate, ApiTokenCreate
from . import models


def create_pipeline_run(data: PipelineRunCreate):
    with SessionLocal() as db:
        db.expire_on_commit = False

        created_model = models.PipelineRun(**data.model_dump())
        db.add(created_model)
        db.commit()
        db.refresh(created_model)
    return created_model


def update_pipeline_run(
    pipeline_run: models.PipelineRun, end_time: datetime, status: PipelineRunStatus
):
    pipeline_run.duration = (end_time - pipeline_run.start_time).total_seconds() * 1000
    pipeline_run.status = status.value
    with SessionLocal() as db:

        db.query(models.PipelineRun).filter(
            models.PipelineRun.id == pipeline_run.id
        ).update(
            dict(
                duration=pipeline_run.duration,
                status=pipeline_run.status,
                tasks_run=pipeline_run.tasks_run,
            )
        )
        db.commit()


def list_pipeline_runs(
    pipeline_id: Optional[str] = None, trigger_id: Optional[str] = None
):
    filters = []
    if pipeline_id:
        filters.append(models.PipelineRun.pipeline_id == pipeline_id)
    if trigger_id:
        filters.append(models.PipelineRun.trigger_id == trigger_id)

    with SessionLocal() as db:
        db.expire_on_commit = False

        pipeline_runs: List[models.PipelineRun] = (
            db.query(models.PipelineRun)
            .filter(*filters)
            .order_by(models.PipelineRun.id.desc())
            .limit(30)
            .all()
        )

    return pipeline_runs


def get_pipeline_run(pipeline_run_id: int) -> Optional[models.PipelineRun]:
    with SessionLocal() as db:

        pipeline_run: Optional[models.PipelineRun] = db.query(models.PipelineRun).get(
            pipeline_run_id
        )

    return pipeline_run


def get_latest_pipeline_run(pipeline_id, trigger_id):
    with SessionLocal() as db:

        pipeline_run: models.PipelineRun = (
            db.query(models.PipelineRun)
            .filter(
                models.PipelineRun.pipeline_id == pipeline_id,
                models.PipelineRun.trigger_id == trigger_id,
            )
            .order_by(models.PipelineRun.id.desc())
            .first()
        )

    return pipeline_run


# API Token functions
def create_api_token(data: ApiTokenCreate, token: str) -> models.ApiToken:
    """Create a new API token."""
    with SessionLocal() as db:
        db.expire_on_commit = False

        created_model = models.ApiToken(
            name=data.name,
            token=token,
            created_at=datetime.now(),
            is_active=True
        )
        db.add(created_model)
        db.commit()
        db.refresh(created_model)
    return created_model


def list_api_tokens() -> List[models.ApiToken]:
    """List all API tokens."""
    with SessionLocal() as db:
        db.expire_on_commit = False

        tokens: List[models.ApiToken] = (
            db.query(models.ApiToken)
            .filter(models.ApiToken.is_active == True)
            .order_by(models.ApiToken.created_at.desc())
            .all()
        )

    return tokens


def get_api_token_by_token(token: str) -> Optional[models.ApiToken]:
    """Get an API token by its token value."""
    with SessionLocal() as db:
        db.expire_on_commit = False

        api_token: Optional[models.ApiToken] = (
            db.query(models.ApiToken)
            .filter(
                models.ApiToken.token == token,
                models.ApiToken.is_active == True
            )
            .first()
        )

    return api_token


def update_api_token_last_used(token_id: int) -> None:
    """Update the last_used_at timestamp for an API token."""
    with SessionLocal() as db:
        db.query(models.ApiToken).filter(
            models.ApiToken.id == token_id
        ).update(
            dict(last_used_at=datetime.now(timezone.utc))
        )
        db.commit()


def delete_api_token(token_id: int) -> bool:
    """Soft delete an API token by marking it as inactive."""
    with SessionLocal() as db:
        result = db.query(models.ApiToken).filter(
            models.ApiToken.id == token_id
        ).update(
            dict(is_active=False)
        )
        db.commit()
        return result > 0
