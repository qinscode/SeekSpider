import pytest
from fastapi.testclient import TestClient
from apscheduler.triggers.interval import IntervalTrigger

from plombery import Pipeline, task
from plombery import _Plombery as Plombery
from plombery.api import app as fastapi_app
from plombery.database.repository import create_pipeline_run, list_pipeline_runs
from plombery.database.schemas import PipelineRunCreate
from plombery.orchestrator import orchestrator
from plombery.orchestrator.executor import run, utcnow
from plombery.pipeline import Trigger
from plombery.pipeline_state import (
    get_pipelines_state,
    pipeline_schedule_is_enabled,
    set_pipeline_schedule_state,
    set_pipelines_state,
)
from plombery.schemas import PipelineRunStatus

client = TestClient(fastapi_app)


@pytest.fixture(autouse=True)
def reset_pipeline_state():
    previous_state = get_pipelines_state()
    set_pipelines_state(True)
    yield
    set_pipelines_state(previous_state["pipelines_enabled"])


def test_pipeline_state_endpoints_toggle():
    response = client.get("/api/pipelines/state")
    assert response.status_code == 200
    assert response.json()["pipelines_enabled"] is True

    response = client.post(
        "/api/pipelines/state", json={"pipelines_enabled": False}
    )
    assert response.status_code == 200
    assert response.json()["pipelines_enabled"] is False

    response = client.get("/api/pipelines/state")
    assert response.status_code == 200
    assert response.json()["pipelines_enabled"] is False


@pytest.mark.asyncio
async def test_manual_run_blocked_when_disabled(app: Plombery):
    set_pipelines_state(False)

    @task
    async def sample_task():
        return True

    pipeline = Pipeline(id="toggle_manual_block", tasks=[sample_task])
    app.register_pipeline(pipeline)

    response = client.post(
        f"/api/pipelines/{pipeline.id}/run", json={"reason": "test"}
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_pipeline_run_cancelled_when_disabled(app: Plombery):
    executed = {"ran": False}

    @task
    async def sample_task():
        executed["ran"] = True

    pipeline = Pipeline(id="toggle_disabled_run", tasks=[sample_task])
    app.register_pipeline(pipeline)

    set_pipelines_state(False)

    await run(pipeline)

    runs = list_pipeline_runs(pipeline_id=pipeline.id)
    assert runs
    assert runs[0].status == PipelineRunStatus.CANCELLED.value
    assert executed["ran"] is False


def test_pipeline_schedule_state_endpoints(app: Plombery):
    @task
    async def sample_task():
        return True

    trigger = Trigger(
        id="interval",
        name="Every minute",
        schedule=IntervalTrigger(minutes=1),
    )

    pipeline = Pipeline(
        id="toggle_schedule_state",
        tasks=[sample_task],
        triggers=[trigger],
    )
    app.register_pipeline(pipeline)

    response = client.get(f"/api/pipelines/{pipeline.id}/schedule")
    assert response.status_code == 200
    assert response.json()["schedule_enabled"] is True
    assert pipeline_schedule_is_enabled(pipeline.id) is True
    assert orchestrator.get_job(pipeline.id, trigger.id) is not None

    response = client.post(
        f"/api/pipelines/{pipeline.id}/schedule",
        json={"schedule_enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["schedule_enabled"] is False
    assert pipeline_schedule_is_enabled(pipeline.id) is False
    assert orchestrator.get_job(pipeline.id, trigger.id) is None

    response = client.post(
        f"/api/pipelines/{pipeline.id}/schedule",
        json={"schedule_enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["schedule_enabled"] is True
    assert orchestrator.get_job(pipeline.id, trigger.id) is not None


@pytest.mark.asyncio
async def test_schedule_toggle_blocks_scheduled_not_manual(app: Plombery):
    executions = {"count": 0}

    @task
    async def sample_task():
        executions["count"] += 1

    trigger = Trigger(
        id="scheduled",
        name="Every minute",
        schedule=IntervalTrigger(minutes=1),
    )
    pipeline = Pipeline(
        id="schedule_toggle_pipeline",
        tasks=[sample_task],
        triggers=[trigger],
    )
    app.register_pipeline(pipeline)

    set_pipeline_schedule_state(pipeline.id, False)
    orchestrator.apply_pipeline_schedule_state(pipeline.id, False)

    await run(pipeline, trigger=trigger)

    manual_run = create_pipeline_run(
        PipelineRunCreate(
            start_time=utcnow(),
            pipeline_id=pipeline.id,
            trigger_id=trigger.id,
            status=PipelineRunStatus.PENDING,
            input_params=None,
            reason="api",
        )
    )

    await run(pipeline, trigger=trigger, pipeline_run=manual_run)

    runs = list_pipeline_runs(pipeline_id=pipeline.id)
    assert len(runs) == 2

    statuses = {r.status for r in runs}
    reasons = {r.reason for r in runs}

    assert PipelineRunStatus.CANCELLED.value in statuses
    assert "schedule_disabled" in reasons
    assert PipelineRunStatus.COMPLETED.value in statuses
    assert executions["count"] == 1
