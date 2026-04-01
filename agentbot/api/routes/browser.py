"""Explicit browser automation routes."""

from __future__ import annotations

from fastapi import APIRouter

from agentbot.services.browser import BrowserTaskService

from ..schemas import BrowserTaskRequest, BrowserTaskResponse

router = APIRouter(prefix="/api/browser", tags=["browser"])


def _browser_service() -> BrowserTaskService:
    return BrowserTaskService()


@router.post("/tasks", response_model=BrowserTaskResponse)
def run_browser_task(request: BrowserTaskRequest):
    result = _browser_service().run_task(
        task=request.task,
        start_url=request.start_url,
        max_steps=request.max_steps,
    )
    return result.model_dump()
