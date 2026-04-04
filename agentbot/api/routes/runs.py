"""Run and run-step routes backed by SQLite shadow storage."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agentbot.api.schemas import RunArtifactsDetail, RunDetail, RunStepsDetail
from agentbot.api.serializers import serialize_artifact, serialize_run, serialize_run_step
from agentbot.services.run_queries import RunQueries

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _run_queries() -> RunQueries:
    return RunQueries()


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str):
    queries = _run_queries()
    try:
        run = queries.get_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"run": serialize_run(run)}


@router.get("/{run_id}/steps", response_model=RunStepsDetail)
def get_run_steps(run_id: str):
    queries = _run_queries()
    try:
        result = queries.get_run_steps(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run": serialize_run(result.run),
        "steps": [serialize_run_step(step) for step in result.steps],
    }


@router.get("/{run_id}/artifacts", response_model=RunArtifactsDetail)
def get_run_artifacts(run_id: str):
    queries = _run_queries()
    try:
        result = queries.get_run_artifacts(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run": serialize_run(result.run),
        "artifacts": [serialize_artifact(artifact) for artifact in result.artifacts],
    }
