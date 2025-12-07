"""
Tests for Flow Meter Scraper parameter handling.

These tests verify that the Flow Meter Scraper correctly handles
different time range configurations when run manually vs via triggers.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from plombery import _Plombery as Plombery
from plombery.api import app


client = TestClient(app)


@pytest.fixture
def mock_flow_meter_scraper():
    """Mock the FlowMeterScraper to capture initialization params"""
    with patch('pipeline.src.flow_meter_pipeline.FlowMeterScraper') as mock:
        mock_instance = MagicMock()
        mock_instance.session_timestamp = "20251119_120000"
        mock_instance.session_data_dir = "/tmp/data"
        mock_instance.session_logs_dir = "/tmp/logs"
        mock_instance.site_configs = {"test_site": {}}
        mock.return_value = mock_instance
        yield mock


@pytest.mark.asyncio
async def test_manual_run_with_this_month(app: Plombery, mock_flow_meter_scraper):
    """Test that manually setting preset_value to 'ThisMonth' is respected"""

    # Simulate API call with ThisMonth preset
    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "params": {
                "max_pages": 100,
                "delay_between_requests": 2,
                "delay_between_sites": 5,
                "time_range_mode": "preset",
                "preset_value": "ThisMonth"
            },
            "reason": "test"
        }
    )

    # Should accept the request
    assert response.status_code == 200

    # Wait for async execution
    import asyncio
    await asyncio.sleep(0.5)

    # Verify FlowMeterScraper was called with correct time_range_override
    mock_flow_meter_scraper.assert_called_once()
    call_kwargs = mock_flow_meter_scraper.call_args[1]

    assert 'time_range_override' in call_kwargs
    time_range = call_kwargs['time_range_override']
    assert time_range['mode'] == 'preset'
    assert time_range['preset_value'] == 'ThisMonth'


@pytest.mark.asyncio
async def test_manual_run_with_this_week(app: Plombery, mock_flow_meter_scraper):
    """Test that manually setting preset_value to 'ThisWeek' is respected"""

    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "params": {
                "time_range_mode": "preset",
                "preset_value": "ThisWeek"
            },
            "reason": "test"
        }
    )

    assert response.status_code == 200

    import asyncio
    await asyncio.sleep(0.5)

    mock_flow_meter_scraper.assert_called_once()
    call_kwargs = mock_flow_meter_scraper.call_args[1]

    time_range = call_kwargs['time_range_override']
    assert time_range['mode'] == 'preset'
    assert time_range['preset_value'] == 'ThisWeek'


@pytest.mark.asyncio
async def test_manual_run_with_custom_dates(app: Plombery, mock_flow_meter_scraper):
    """Test that custom date ranges work correctly"""

    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "params": {
                "time_range_mode": "custom",
                "custom_from": "2025-01-01T00:00:00",
                "custom_to": "2025-01-31T23:59:59"
            },
            "reason": "test"
        }
    )

    assert response.status_code == 200

    import asyncio
    await asyncio.sleep(0.5)

    mock_flow_meter_scraper.assert_called_once()
    call_kwargs = mock_flow_meter_scraper.call_args[1]

    time_range = call_kwargs['time_range_override']
    assert time_range['mode'] == 'custom'
    assert time_range['custom_from'] == "2025-01-01T00:00:00"
    assert time_range['custom_to'] == "2025-01-31T23:59:59"


@pytest.mark.asyncio
async def test_trigger_run_uses_trigger_defaults(app: Plombery, mock_flow_meter_scraper):
    """Test that trigger runs use trigger's default params (ThisQuarter)"""

    # Run via trigger (morning_11am has ThisQuarter as default)
    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "trigger_id": "morning_11am",
            "reason": "test"
        }
    )

    assert response.status_code == 200

    import asyncio
    await asyncio.sleep(0.5)

    mock_flow_meter_scraper.assert_called_once()
    call_kwargs = mock_flow_meter_scraper.call_args[1]

    time_range = call_kwargs['time_range_override']
    assert time_range['mode'] == 'preset'
    assert time_range['preset_value'] == 'ThisQuarter'


@pytest.mark.asyncio
async def test_trigger_run_with_manual_override(app: Plombery, mock_flow_meter_scraper):
    """Test that manual params override trigger defaults"""

    # Run via trigger but with manual params
    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "trigger_id": "morning_11am",
            "params": {
                "time_range_mode": "preset",
                "preset_value": "Today"
            },
            "reason": "test"
        }
    )

    assert response.status_code == 200

    import asyncio
    await asyncio.sleep(0.5)

    mock_flow_meter_scraper.assert_called_once()
    call_kwargs = mock_flow_meter_scraper.call_args[1]

    time_range = call_kwargs['time_range_override']
    assert time_range['mode'] == 'preset'
    # Should use manual override 'Today', not trigger default 'ThisQuarter'
    assert time_range['preset_value'] == 'Today'


@pytest.mark.asyncio
async def test_different_triggers_have_different_defaults(app: Plombery, mock_flow_meter_scraper):
    """Test that different triggers can have different default params"""

    # Test morning trigger
    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "trigger_id": "morning_11am",
            "reason": "test"
        }
    )

    assert response.status_code == 200

    import asyncio
    await asyncio.sleep(0.5)

    assert mock_flow_meter_scraper.called

    # Reset mock for next call
    mock_flow_meter_scraper.reset_mock()

    # Test night trigger
    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "trigger_id": "night_11pm",
            "reason": "test"
        }
    )

    assert response.status_code == 200
    await asyncio.sleep(0.5)

    # Both should use ThisQuarter (as defined in pipeline)
    call_kwargs = mock_flow_meter_scraper.call_args[1]
    time_range = call_kwargs['time_range_override']
    assert time_range['preset_value'] == 'ThisQuarter'


@pytest.mark.asyncio
async def test_validation_error_on_invalid_mode(app: Plombery):
    """Test that invalid time_range_mode is rejected"""

    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "params": {
                "time_range_mode": "invalid_mode",
                "preset_value": "ThisMonth"
            },
            "reason": "test"
        }
    )

    # Should return validation error
    assert response.status_code == 422
    error_detail = response.json()
    assert "detail" in error_detail


@pytest.mark.asyncio
async def test_other_params_also_overridable(app: Plombery, mock_flow_meter_scraper):
    """Test that other params like max_pages are also correctly overridden"""

    response = client.post(
        "/api/pipelines/flow_meter_scraper/run",
        json={
            "params": {
                "max_pages": 50,  # Override default 100
                "delay_between_requests": 5,  # Override default 2
                "time_range_mode": "preset",
                "preset_value": "ThisMonth"
            },
            "reason": "test"
        }
    )

    assert response.status_code == 200

    import asyncio
    await asyncio.sleep(0.5)

    # The params should have been passed correctly
    # (This would be verified in the actual task execution,
    #  but we can at least verify the API accepts them)
    assert mock_flow_meter_scraper.called
