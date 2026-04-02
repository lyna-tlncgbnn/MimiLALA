"""Database bootstrap and connection management."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from agentbot.storage.paths import database_path
from agentbot.storage.schema import initialize_schema


class AgentDatabase:
    """Handle SQLite initialization and provide connections for repositories."""

    def __init__(self, path: Path | None = None):
        self.path = path or database_path()

    def initialize(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            initialize_schema(connection)
        return self.path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
