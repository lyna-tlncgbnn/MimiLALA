"""Bootstrap helpers for phase-1 storage rollout."""

from __future__ import annotations

from pathlib import Path

from agentbot.storage.db import AgentDatabase


def ensure_agent_database() -> Path:
    """Create the SQLite database and schema if they do not already exist."""
    database = AgentDatabase()
    return database.initialize()
