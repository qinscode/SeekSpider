import json
import logging
from pathlib import Path
from typing import Dict, TypedDict, cast

from plombery.config import settings

_logger = logging.getLogger(__name__)


class PipelinesState(TypedDict, total=False):
    pipelines_enabled: bool
    pipeline_schedules: Dict[str, bool]


_DEFAULT_STATE: PipelinesState = {
    "pipelines_enabled": True,
    "pipeline_schedules": {},
}
_STATE_FILE_NAME = "pipelines_state.json"
_state_cache: PipelinesState | None = None


def _get_state_path() -> Path:
    """Return the path where the pipelines state is stored."""
    base_dir = settings.data_path / "output"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / _STATE_FILE_NAME


def _load_state_from_disk() -> PipelinesState:
    state_file = _get_state_path()

    if not state_file.exists():
        return _DEFAULT_STATE.copy()

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return {
            "pipelines_enabled": bool(data.get("pipelines_enabled", True)),
            "pipeline_schedules": cast(
                Dict[str, bool], data.get("pipeline_schedules", {})
            ),
        }
    except Exception as exc:  # pragma: no cover - defensive logging
        _logger.warning(
            "Failed to read pipelines state from %s: %s", state_file, exc
        )
        return _DEFAULT_STATE.copy()


def get_pipelines_state() -> PipelinesState:
    """Get the cached pipelines state, loading it from disk if needed."""
    global _state_cache

    if _state_cache is None:
        _state_cache = _load_state_from_disk()

    return _state_cache


def pipelines_are_enabled() -> bool:
    """Return True if pipelines are enabled."""
    return get_pipelines_state().get("pipelines_enabled", True)


def pipeline_schedule_is_enabled(pipeline_id: str) -> bool:
    """Return True if the given pipeline should run on schedule."""
    pipeline_schedules = get_pipelines_state().get("pipeline_schedules", {})
    return pipeline_schedules.get(pipeline_id, True)


def _persist_state(state: PipelinesState) -> PipelinesState:
    state_file = _get_state_path()
    state_file.write_text(json.dumps(state), encoding="utf-8")
    return state


def set_pipelines_state(pipelines_enabled: bool) -> PipelinesState:
    """Persist and cache the pipelines enabled/disabled state."""
    global _state_cache

    current_state = get_pipelines_state()
    state: PipelinesState = {
        "pipelines_enabled": pipelines_enabled,
        "pipeline_schedules": current_state.get("pipeline_schedules", {}),
    }

    _state_cache = _persist_state(state)
    return state


def set_pipeline_schedule_state(
    pipeline_id: str, schedule_enabled: bool
) -> PipelinesState:
    """Persist and cache the schedule-enabled flag for a single pipeline."""
    global _state_cache

    state = get_pipelines_state()
    pipeline_schedules = state.get("pipeline_schedules", {}).copy()
    pipeline_schedules[pipeline_id] = schedule_enabled

    new_state: PipelinesState = {
        "pipelines_enabled": state.get("pipelines_enabled", True),
        "pipeline_schedules": pipeline_schedules,
    }

    _state_cache = _persist_state(new_state)
    return new_state


class PipelinesDisabled(Exception):
    """Raised when pipelines are disabled via the toggle."""


def ensure_pipelines_enabled() -> None:
    if not pipelines_are_enabled():
        raise PipelinesDisabled("Pipelines are disabled")
