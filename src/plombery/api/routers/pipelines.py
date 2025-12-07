from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ValidationError

from plombery.api.authentication import NeedsAuth, NeedsApiTokenAuth
from plombery.database.schemas import PipelineRun
from plombery.orchestrator import orchestrator, run_pipeline_now
from plombery.pipeline.pipeline import Pipeline
from plombery.pipeline.trigger import Trigger
from plombery.pipeline_state import (
    PipelinesDisabled,
    ensure_pipelines_enabled,
    get_pipelines_state,
    pipeline_schedule_is_enabled,
    set_pipeline_schedule_state,
    set_pipelines_state,
)


router = APIRouter(prefix="/pipelines", tags=["Pipelines"], dependencies=[NeedsAuth])

# Create a separate router for external API access with API token auth
external_router = APIRouter(prefix="/external/pipelines", tags=["External API"], dependencies=[NeedsApiTokenAuth])


def _populate_next_fire_time(pipeline: Pipeline) -> None:
    pipeline.schedule_enabled = pipeline_schedule_is_enabled(pipeline.id)

    for trigger in pipeline.triggers:
        if not trigger.schedule:
            continue

        if job := orchestrator.get_job(pipeline.id, trigger.id):
            trigger.next_fire_time = job.next_run_time
        else:
            trigger.next_fire_time = None


@router.get("/", response_model=None, description="List all the registered pipelines")
def list_pipelines():
    pipelines = list(orchestrator.pipelines.values())

    for pipeline in pipelines:
        _populate_next_fire_time(pipeline)

    return jsonable_encoder(
        pipelines,
        custom_encoder=Trigger.Config.json_encoders,
    )


class PipelinesState(BaseModel):
    pipelines_enabled: bool


class PipelineScheduleState(BaseModel):
    schedule_enabled: bool


@router.get(
    "/state",
    response_model=PipelinesState,
    description="Get the pipelines enabled/disabled state",
)
def get_pipelines_state_route():
    return PipelinesState(**get_pipelines_state())


@router.post(
    "/state",
    response_model=PipelinesState,
    description="Update the pipelines enabled/disabled state",
)
def update_pipelines_state_route(body: PipelinesState):
    state = set_pipelines_state(body.pipelines_enabled)
    return PipelinesState(**state)


@router.get(
    "/{pipeline_id}/schedule",
    response_model=PipelineScheduleState,
    description="Get whether a pipeline is allowed to run on schedule",
)
def get_pipeline_schedule_state_route(pipeline_id: str):
    if not orchestrator.get_pipeline(pipeline_id):
        raise HTTPException(404, f"The pipeline with ID {pipeline_id} doesn't exist")

    return PipelineScheduleState(
        schedule_enabled=pipeline_schedule_is_enabled(pipeline_id)
    )


@router.post(
    "/{pipeline_id}/schedule",
    response_model=PipelineScheduleState,
    description="Enable or disable scheduled runs for a pipeline",
)
def update_pipeline_schedule_state_route(
    pipeline_id: str, body: PipelineScheduleState
):
    if not (pipeline := orchestrator.get_pipeline(pipeline_id)):
        raise HTTPException(404, f"The pipeline with ID {pipeline_id} doesn't exist")

    set_pipeline_schedule_state(pipeline_id, body.schedule_enabled)
    orchestrator.apply_pipeline_schedule_state(pipeline_id, body.schedule_enabled)
    pipeline.schedule_enabled = body.schedule_enabled
    _populate_next_fire_time(pipeline)

    return PipelineScheduleState(schedule_enabled=body.schedule_enabled)


def _ensure_pipelines_enabled():
    try:
        ensure_pipelines_enabled()
    except PipelinesDisabled as exc:
        raise HTTPException(status_code=409, detail=str(exc))


async def _run_pipeline_now_safe(
    pipeline: Pipeline,
    trigger: Optional[Trigger] = None,
    params: Optional[Dict[str, Any]] = None,
    reason: str = "api",
):
    try:
        return await run_pipeline_now(
            pipeline, trigger=trigger, params=params, reason=reason
        )
    except PipelinesDisabled as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{pipeline_id}", response_model=None, description="Get a single pipeline")
def get_pipeline(pipeline_id: str):
    if not (pipeline := orchestrator.get_pipeline(pipeline_id)):
        raise HTTPException(404, f"The pipeline with ID {pipeline_id} doesn't exist")

    _populate_next_fire_time(pipeline)

    return jsonable_encoder(pipeline, custom_encoder=Trigger.Config.json_encoders)


@router.get(
    "/{pipeline_id}/input-schema",
    description="Get the JSON schema of the input parameters for a pipeline",
)
def get_pipeline_input_schema(pipeline_id: str):
    if not (pipeline := orchestrator.get_pipeline(pipeline_id)):
        raise HTTPException(404, f"The pipeline with ID {pipeline_id} doesn't exist")

    return pipeline.params.model_json_schema() if pipeline.params else dict()


class PipelineRunInput(BaseModel):
    trigger_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    reason: str = "api"


@router.post("/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, body: PipelineRunInput) -> PipelineRun:
    if not (pipeline := orchestrator.get_pipeline(pipeline_id)):
        raise HTTPException(404, f"The pipeline with ID {pipeline_id} doesn't exist")

    _ensure_pipelines_enabled()

    if body.trigger_id:
        triggers = [
            trigger for trigger in pipeline.triggers if trigger.id == body.trigger_id
        ]

        if len(triggers) == 0:
            raise HTTPException(
                status_code=404, detail=f"Trigger {body.trigger_id} not found"
            )

        trigger = triggers[0]

        return await _run_pipeline_now_safe(
            pipeline, trigger=trigger, params=body.params, reason=body.reason
        )
    else:
        if pipeline.params:
            try:
                pipeline.params.model_validate(body.params)
            except ValidationError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=exc.errors(),
                )

        return await _run_pipeline_now_safe(
            pipeline,
            params=body.params,
            reason=body.reason,
        )


# External API endpoints (with API token authentication)
@external_router.post("/{pipeline_id}/run")
async def run_pipeline_external(pipeline_id: str, body: PipelineRunInput) -> PipelineRun:
    """
    Trigger a pipeline run using API token authentication.

    This endpoint is designed for external API access. You must provide a valid API token
    in the Authorization header as a Bearer token.

    Example:
    ```
    curl -X POST https://your-domain.com/api/external/pipelines/flow_meter_scraper/run \
      -H "Authorization: Bearer plb_your_api_token_here" \
      -H "Content-Type: application/json" \
      -d '{
        "params": {
          "max_pages": 100,
          "delay_between_requests": 2,
          "delay_between_sites": 5,
          "time_range_mode": "preset",
          "preset_value": "ThisMonth"
        }
      }'
    ```
    """
    if not (pipeline := orchestrator.get_pipeline(pipeline_id)):
        raise HTTPException(404, f"The pipeline with ID {pipeline_id} doesn't exist")

    _ensure_pipelines_enabled()

    if body.trigger_id:
        triggers = [
            trigger for trigger in pipeline.triggers if trigger.id == body.trigger_id
        ]

        if len(triggers) == 0:
            raise HTTPException(
                status_code=404, detail=f"Trigger {body.trigger_id} not found"
            )

        trigger = triggers[0]

        return await _run_pipeline_now_safe(
            pipeline, trigger=trigger, params=body.params, reason=body.reason
        )
    else:
        if pipeline.params:
            try:
                pipeline.params.model_validate(body.params)
            except ValidationError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=exc.errors(),
                )

        return await _run_pipeline_now_safe(
            pipeline,
            params=body.params,
            reason=body.reason,
        )


@external_router.get("/{pipeline_id}")
def get_pipeline_external(pipeline_id: str):
    """Get pipeline information using API token authentication."""
    if not (pipeline := orchestrator.get_pipeline(pipeline_id)):
        raise HTTPException(404, f"The pipeline with ID {pipeline_id} doesn't exist")

    _populate_next_fire_time(pipeline)

    return jsonable_encoder(pipeline, custom_encoder=Trigger.Config.json_encoders)


@external_router.get("/{pipeline_id}/input-schema")
def get_pipeline_input_schema_external(pipeline_id: str):
    """Get the JSON schema of the input parameters for a pipeline (external API)."""
    if not (pipeline := orchestrator.get_pipeline(pipeline_id)):
        raise HTTPException(404, f"The pipeline with ID {pipeline_id} doesn't exist")

    return pipeline.params.model_json_schema() if pipeline.params else dict()
