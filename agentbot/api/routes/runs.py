"""Run and run-step routes backed by SQLite shadow storage."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agentbot.api.schemas import RunDetail, RunStepsDetail
from agentbot.api.serializers import serialize_run, serialize_run_step
from agentbot.storage.db import AgentDatabase
from agentbot.storage.repositories import RunRepository, RunStepRepository

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str):
    database = AgentDatabase()
    database.initialize()
    with database.connect() as connection:
        run_repo = RunRepository(connection)
        run = run_repo.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        return {"run": serialize_run(run)}


@router.get("/{run_id}/steps", response_model=RunStepsDetail)
def get_run_steps(run_id: str):
    database = AgentDatabase()
    database.initialize()
    with database.connect() as connection:
        run_repo = RunRepository(connection)
        step_repo = RunStepRepository(connection)

        run = run_repo.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        steps = step_repo.list_for_run(run_id)
        return {
            "run": serialize_run(run),
            "steps": [serialize_run_step(step) for step in steps],
        }
