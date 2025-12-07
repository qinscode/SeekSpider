# Testing Guide for Parameter Priority

This directory contains tests for verifying that pipeline parameters are correctly prioritized and passed through the system.

## Test Files

### 1. `test_params_priority.py`
Tests the general parameter priority mechanism across all pipelines:

- **Manual params override trigger params**: When you manually run a pipeline with custom parameters, they should take precedence over the trigger's default parameters
- **Trigger params override default params**: When a pipeline is triggered automatically, the trigger's parameters should override the pipeline's default parameters
- **Default params as fallback**: When no manual or trigger params are provided, the pipeline's default parameters should be used
- **Partial parameter overrides**: Only specified parameters are overridden, others use defaults
- **API endpoint integration**: The API correctly passes manual parameters through to the executor

### 2. `test_flow_meter_params.py`
Tests specific to the Flow Meter Scraper pipeline:

- **ThisMonth preset override**: Manually setting `preset_value` to "ThisMonth" overrides the default "ThisQuarter"
- **ThisWeek preset**: Setting `preset_value` to "ThisWeek" works correctly
- **Custom date ranges**: Custom date ranges (`custom_from`, `custom_to`) are properly handled
- **Trigger defaults**: Triggers use their configured default parameters when no override is provided
- **Manual override of triggers**: Manual parameters override trigger defaults even when running via a trigger
- **Other parameters**: Parameters like `max_pages` and `delay_between_requests` are also correctly overridden
- **Validation**: Invalid parameter values are properly rejected with 422 errors

## Running the Tests

### Run all parameter tests:
```bash
pytest tests/test_params_priority.py tests/test_flow_meter_params.py -v
```

### Run only parameter priority tests:
```bash
pytest tests/test_params_priority.py -v
```

### Run only Flow Meter specific tests:
```bash
pytest tests/test_flow_meter_params.py -v
```

### Run a specific test:
```bash
pytest tests/test_params_priority.py::test_manual_params_override_trigger_params -v
```

### Run with output:
```bash
pytest tests/test_params_priority.py -v -s
```

## Test Scenarios Covered

### Scenario 1: Manual Run with Custom Parameters
**What happens**: User runs Flow Meter Scraper manually and sets `preset_value: "ThisMonth"`

**Expected behavior**: The scraper should use "ThisMonth", not the default "ThisQuarter"

**Test**: `test_manual_run_with_this_month` in `test_flow_meter_params.py`

### Scenario 2: Scheduled Trigger Run
**What happens**: The `morning_11am` trigger runs automatically

**Expected behavior**: Should use the trigger's default params (`preset_value: "ThisQuarter"`)

**Test**: `test_trigger_run_uses_trigger_defaults` in `test_flow_meter_params.py`

### Scenario 3: Trigger Run with Manual Override
**What happens**: User runs via a trigger but provides custom parameters

**Expected behavior**: Manual params should override the trigger's defaults

**Test**: `test_trigger_run_with_manual_override` in `test_flow_meter_params.py`

### Scenario 4: Parameter Priority Chain
**What happens**: Testing the full priority chain: manual > trigger > default

**Expected behavior**: Higher priority params always win

**Tests**: Various tests in `test_params_priority.py`

## Code Coverage

These tests cover:

1. **API Layer** (`src/plombery/api/routers/pipelines.py`):
   - `POST /api/pipelines/{pipeline_id}/run`
   - Parameter validation
   - Passing params to orchestrator

2. **Orchestrator Layer** (`src/plombery/orchestrator/__init__.py`):
   - `run_pipeline_now` function
   - Parameter passing to executor

3. **Executor Layer** (`src/plombery/orchestrator/executor.py`):
   - `run` function
   - Parameter priority logic
   - Pydantic model instantiation

4. **Pipeline Layer** (`pipeline/src/flow_meter_pipeline.py`):
   - FlowMeterParams handling
   - Time range configuration
   - Scraper initialization

## Debugging Test Failures

If a test fails, check:

1. **Parameter priority logic**: Verify the logic in `executor.py:113-125`
2. **API parameter passing**: Check `pipelines.py:82-84`
3. **Parameter validation**: Ensure Pydantic models are correctly defined
4. **Mock configuration**: In Flow Meter tests, ensure mocks are properly set up

## Adding New Tests

When adding new parameter-related features:

1. Add unit tests to `test_params_priority.py` for the general mechanism
2. Add integration tests to `test_flow_meter_params.py` for Flow Meter specific behavior
3. Follow the existing test patterns
4. Use the `reset_params` fixture to avoid test pollution
5. Add appropriate documentation in this file

## Known Issues

None currently.

## Future Improvements

- Add performance tests for parameter validation
- Add tests for parameter type coercion
- Add tests for complex nested parameters
- Add integration tests with actual database
