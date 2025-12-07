"""
Tests for parameter priority in pipeline execution.

This test suite verifies that parameters are correctly prioritized:
1. Manually passed params (highest priority)
2. Trigger default params
3. Pipeline default params (lowest priority)
"""

import pytest
from pydantic import BaseModel, Field
from fastapi.testclient import TestClient

from plombery import _Plombery as Plombery
from plombery import task, Pipeline, Trigger
from plombery.api import app
from plombery.orchestrator import run_pipeline_now
from plombery.orchestrator.executor import run


client = TestClient(app)


# Define test parameter models
class TestParams(BaseModel):
    """Test parameters for pipeline"""
    value: str = Field(default="default_value")
    number: int = Field(default=0)


# Store the last params that were used in task execution
last_params_used = None


@task
async def test_task(params: TestParams):
    """Test task that records the params it receives"""
    global last_params_used
    last_params_used = params
    return {"value": params.value, "number": params.number}


@pytest.fixture
def reset_params():
    """Reset global params before each test"""
    global last_params_used
    last_params_used = None
    yield
    last_params_used = None


@pytest.mark.asyncio
async def test_manual_params_override_trigger_params(app: Plombery, reset_params):
    """Test that manually passed params override trigger params"""

    # Create pipeline with trigger that has default params
    pipeline = Pipeline(
        id="test_pipeline",
        tasks=[test_task],
        params=TestParams,
        triggers=[
            Trigger(
                id="test_trigger",
                params=TestParams(value="trigger_value", number=10)
            )
        ]
    )

    app.register_pipeline(pipeline)
    trigger = pipeline.triggers[0]

    # Run with manual params (should override trigger params)
    manual_params = {"value": "manual_value", "number": 99}

    await run(
        pipeline=pipeline,
        trigger=trigger,
        params=manual_params
    )

    # Verify manual params were used
    assert last_params_used is not None
    assert last_params_used.value == "manual_value"
    assert last_params_used.number == 99


@pytest.mark.asyncio
async def test_trigger_params_override_default_params(app: Plombery, reset_params):
    """Test that trigger params override pipeline default params"""

    # Create pipeline with trigger that has params
    pipeline = Pipeline(
        id="test_pipeline",
        tasks=[test_task],
        params=TestParams,
        triggers=[
            Trigger(
                id="test_trigger",
                params=TestParams(value="trigger_value", number=10)
            )
        ]
    )

    app.register_pipeline(pipeline)
    trigger = pipeline.triggers[0]

    # Run with trigger (no manual params)
    await run(
        pipeline=pipeline,
        trigger=trigger,
        params=None
    )

    # Verify trigger params were used
    assert last_params_used is not None
    assert last_params_used.value == "trigger_value"
    assert last_params_used.number == 10


@pytest.mark.asyncio
async def test_default_params_when_no_override(app: Plombery, reset_params):
    """Test that default params are used when no override provided"""

    # Create pipeline without trigger params
    pipeline = Pipeline(
        id="test_pipeline",
        tasks=[test_task],
        params=TestParams
    )

    app.register_pipeline(pipeline)

    # Run without trigger and without manual params
    await run(
        pipeline=pipeline,
        trigger=None,
        params=None
    )

    # Verify default params were used
    assert last_params_used is not None
    assert last_params_used.value == "default_value"
    assert last_params_used.number == 0


@pytest.mark.asyncio
async def test_partial_manual_params_merge(app: Plombery, reset_params):
    """Test that partial manual params work correctly"""

    # Create pipeline with trigger params
    pipeline = Pipeline(
        id="test_pipeline",
        tasks=[test_task],
        params=TestParams,
        triggers=[
            Trigger(
                id="test_trigger",
                params=TestParams(value="trigger_value", number=10)
            )
        ]
    )

    app.register_pipeline(pipeline)
    trigger = pipeline.triggers[0]

    # Run with only partial manual params (only override 'value')
    manual_params = {"value": "partial_manual"}

    await run(
        pipeline=pipeline,
        trigger=trigger,
        params=manual_params
    )

    # Manual params should be used, with default for unspecified fields
    assert last_params_used is not None
    assert last_params_used.value == "partial_manual"
    assert last_params_used.number == 0  # default value, not trigger value


@pytest.mark.asyncio
async def test_api_run_with_manual_params(app: Plombery, reset_params):
    """Test API endpoint correctly passes manual params"""

    # Create pipeline with trigger
    pipeline = Pipeline(
        id="test_pipeline",
        tasks=[test_task],
        params=TestParams,
        triggers=[
            Trigger(
                id="test_trigger",
                params=TestParams(value="trigger_value", number=10)
            )
        ]
    )

    app.register_pipeline(pipeline)

    # Make API request with manual params
    response = client.post(
        "/api/pipelines/test_pipeline/run",
        json={
            "trigger_id": "test_trigger",
            "params": {
                "value": "api_manual_value",
                "number": 777
            },
            "reason": "test"
        }
    )

    assert response.status_code == 200

    # Wait a bit for async execution
    import asyncio
    await asyncio.sleep(0.5)

    # Verify manual params from API were used
    assert last_params_used is not None
    assert last_params_used.value == "api_manual_value"
    assert last_params_used.number == 777


@pytest.mark.asyncio
async def test_api_run_without_manual_params(app: Plombery, reset_params):
    """Test API endpoint uses trigger params when no manual params provided"""

    # Create pipeline with trigger
    pipeline = Pipeline(
        id="test_pipeline",
        tasks=[test_task],
        params=TestParams,
        triggers=[
            Trigger(
                id="test_trigger",
                params=TestParams(value="trigger_value", number=10)
            )
        ]
    )

    app.register_pipeline(pipeline)

    # Make API request without manual params
    response = client.post(
        "/api/pipelines/test_pipeline/run",
        json={
            "trigger_id": "test_trigger",
            "reason": "test"
        }
    )

    assert response.status_code == 200

    # Wait a bit for async execution
    import asyncio
    await asyncio.sleep(0.5)

    # Verify trigger params were used
    assert last_params_used is not None
    assert last_params_used.value == "trigger_value"
    assert last_params_used.number == 10


@pytest.mark.asyncio
async def test_api_run_manual_no_trigger(app: Plombery, reset_params):
    """Test API endpoint with manual params but no trigger"""

    # Create pipeline without trigger
    pipeline = Pipeline(
        id="test_pipeline",
        tasks=[test_task],
        params=TestParams
    )

    app.register_pipeline(pipeline)

    # Make API request with manual params but no trigger
    response = client.post(
        "/api/pipelines/test_pipeline/run",
        json={
            "params": {
                "value": "manual_no_trigger",
                "number": 888
            },
            "reason": "test"
        }
    )

    assert response.status_code == 200

    # Wait a bit for async execution
    import asyncio
    await asyncio.sleep(0.5)

    # Verify manual params were used
    assert last_params_used is not None
    assert last_params_used.value == "manual_no_trigger"
    assert last_params_used.number == 888


@pytest.mark.asyncio
async def test_empty_params_dict(app: Plombery, reset_params):
    """Test that empty params dict uses default params"""

    # Create pipeline
    pipeline = Pipeline(
        id="test_pipeline",
        tasks=[test_task],
        params=TestParams
    )

    app.register_pipeline(pipeline)

    # Run with empty params dict
    await run(
        pipeline=pipeline,
        trigger=None,
        params={}
    )

    # Empty dict is falsy in Python, so should use defaults
    assert last_params_used is not None
    assert last_params_used.value == "default_value"
    assert last_params_used.number == 0
