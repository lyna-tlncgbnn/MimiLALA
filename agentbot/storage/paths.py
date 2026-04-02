"""Filesystem paths used by the new storage layer."""

from __future__ import annotations

from pathlib import Path

WORKSPACE_DIR_NAME = "workspace"
DATABASE_FILE_NAME = "agent_runtime.db"
CHECKPOINT_DATABASE_FILE_NAME = "langgraph_checkpoints.db"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def workspace_root() -> Path:
    return repo_root() / WORKSPACE_DIR_NAME


def database_path() -> Path:
    return workspace_root() / DATABASE_FILE_NAME


def checkpoints_path() -> Path:
    return workspace_root() / CHECKPOINT_DATABASE_FILE_NAME
