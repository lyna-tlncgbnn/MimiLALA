"""Structured decision models for the main supervisor node."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


SupervisorDecisionName = Literal["respond", "tools", "browser"]


class SupervisorDecision(BaseModel):
    """Main-agent orchestration decision for the current turn."""

    decision: SupervisorDecisionName
    reason: str = Field(min_length=1)
    response: str | None = None
    browser_task: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "SupervisorDecision":
        if self.decision == "respond" and not self.response:
            raise ValueError("respond decision requires response")
        if self.decision == "browser" and not self.browser_task:
            raise ValueError("browser decision requires browser_task")
        return self
