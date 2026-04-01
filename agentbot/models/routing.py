"""Structured routing models for the main chat graph."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RouteName = Literal["chat", "browser"]


class RoutingDecision(BaseModel):
    """Minimal, explainable route choice emitted by the router model."""

    route: RouteName
    reason: str = Field(min_length=1)
