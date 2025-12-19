from typing import Optional, Sequence
from pathlib import Path
import json
import os

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from plombery.api.authentication import NeedsAuth
from plombery.database.schemas import PipelineRun
from plombery.exceptions import InvalidDataPath
from plombery.orchestrator.data_storage import get_task_run_data_file, read_logs_file
from plombery.database.repository import list_pipeline_runs, get_pipeline_run
from plombery.config import settings
from plombery.orchestrator import cancel_pipeline_run


class JSONLResponse(Response):
    media_type = "application/jsonl"


router = APIRouter(
    prefix="/runs",
    tags=["Runs"],
    dependencies=[NeedsAuth],
)


@router.get("/")
def list_runs(
    pipeline_id: Optional[str] = None,
    trigger_id: Optional[str] = None,
) -> Sequence[PipelineRun]:
    return list_pipeline_runs(pipeline_id=pipeline_id, trigger_id=trigger_id)


@router.get("/{run_id}")
def get_run(run_id: int) -> PipelineRun:
    if not (pipeline_run := get_pipeline_run(run_id)):
        raise HTTPException(404, f"The pipeline run {run_id} doesn't exist")

    return pipeline_run


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: int) -> dict:
    """Cancel a running pipeline"""
    if not (pipeline_run := get_pipeline_run(run_id)):
        raise HTTPException(404, f"The pipeline run {run_id} doesn't exist")

    if pipeline_run.status != "running":
        raise HTTPException(400, f"Pipeline run {run_id} is not running (status: {pipeline_run.status})")

    try:
        await cancel_pipeline_run(run_id)
        return {"message": f"Pipeline run {run_id} has been cancelled", "run_id": run_id}
    except Exception as e:
        raise HTTPException(500, f"Failed to cancel pipeline run: {str(e)}")


@router.get("/{run_id}/logs", response_class=JSONLResponse)
def get_run_logs(run_id: int):
    try:
        logs = read_logs_file(run_id)
    except InvalidDataPath:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    return Response(content=logs, media_type="application/jsonl")


@router.get("/{run_id}/data/{task}")
def get_run_data(run_id: int, task: str):
    try:
        data_file = get_task_run_data_file(run_id, task)
    except InvalidDataPath:
        raise HTTPException(status_code=400, detail="Invalid run or task ID")

    if not data_file.exists():
        raise HTTPException(status_code=404, detail="Task has no data")

    return FileResponse(path=data_file, filename=f"run-{run_id}-{task}-data.json")


def _resolve_path(path_str: str) -> Path:
    """
    Resolve a path that could be absolute or relative.
    If relative, resolve it relative to the data_path.
    """
    path = Path(path_str)
    if path.is_absolute():
        return path
    # Resolve relative to the project data path
    return (settings.data_path / path).resolve()


@router.get("/{run_id}/scraper-logs")
def list_scraper_logs(run_id: int):
    """List all scraper log files for a given run"""
    # Get the pipeline run to access task information
    pipeline_run = get_pipeline_run(run_id)
    if not pipeline_run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    # Try to find logs_dir from any task's output
    logs_dir = None
    for task_run in pipeline_run.tasks_run:
        try:
            data_file = get_task_run_data_file(run_id, task_run.task_id)
            if not data_file.exists():
                continue

            with data_file.open(mode="r", encoding="utf-8") as f:
                task_output = json.load(f)

            if "logs_dir" in task_output:
                logs_dir = task_output["logs_dir"]
                break
        except Exception:
            continue

    if not logs_dir:
        return []

    # Read the logs directory
    try:
        # Resolve path (handles both absolute and relative paths)
        logs_path = _resolve_path(logs_dir)

        if not logs_path.exists() or not logs_path.is_dir():
            return []

        # List all .log files in the directory
        log_files = []
        for log_file in logs_path.glob("*.log"):
            log_files.append({
                "filename": log_file.name,
                "size": log_file.stat().st_size,
                "modified": log_file.stat().st_mtime,
            })

        # Sort by filename
        log_files.sort(key=lambda x: x["filename"])
        return log_files

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs directory: {str(e)}")


@router.get("/{run_id}/scraper-logs/{log_filename}")
def get_scraper_log(run_id: int, log_filename: str):
    """Get the content of a specific scraper log file"""
    # Security: validate filename to prevent directory traversal
    if "/" in log_filename or "\\" in log_filename or ".." in log_filename:
        raise HTTPException(status_code=400, detail="Invalid log filename")

    # Get the pipeline run to access task information
    pipeline_run = get_pipeline_run(run_id)
    if not pipeline_run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    # Try to find logs_dir from any task's output
    logs_dir = None
    for task_run in pipeline_run.tasks_run:
        try:
            data_file = get_task_run_data_file(run_id, task_run.task_id)
            if not data_file.exists():
                continue

            with data_file.open(mode="r", encoding="utf-8") as f:
                task_output = json.load(f)

            if "logs_dir" in task_output:
                logs_dir = task_output["logs_dir"]
                break
        except Exception:
            continue

    if not logs_dir:
        raise HTTPException(status_code=404, detail="Logs directory not found in task output")

    # Read the log file
    try:
        # Resolve path (handles both absolute and relative paths)
        logs_path = _resolve_path(logs_dir)
        log_file_path = logs_path / log_filename

        # Ensure the log file is actually within the logs directory (security check)
        try:
            log_file_path.resolve().relative_to(logs_path.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid log file path")

        if not log_file_path.exists():
            raise HTTPException(status_code=404, detail="Log file not found")

        # Read and return the log file content
        with log_file_path.open(mode="r", encoding="utf-8") as f:
            content = f.read()

        return Response(content=content, media_type="text/plain; charset=utf-8")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")
