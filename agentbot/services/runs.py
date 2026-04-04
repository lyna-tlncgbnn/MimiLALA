"""Compatibility wrapper around run query use cases."""

from __future__ import annotations

from agentbot.services.run_queries import RunArtifactsResult, RunQueries, RunStepsResult


class RunService(RunQueries):
    """Backward-compatible alias for the older service entrypoint."""


__all__ = ["RunArtifactsResult", "RunService", "RunStepsResult"]
