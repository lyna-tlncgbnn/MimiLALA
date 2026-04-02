"""Artifact repository."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbot.storage.common import new_prefixed_id, now_iso
from agentbot.storage.models import ArtifactRow


class ArtifactRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(
        self,
        *,
        run_id: str,
        artifact_type: str,
        name: str,
        uri: str,
        step_id: str | None = None,
        metadata: Any = None,
    ) -> ArtifactRow:
        row = ArtifactRow(
            artifact_id=new_prefixed_id("artifact"),
            run_id=run_id,
            artifact_type=artifact_type,
            name=name,
            uri=uri,
            created_at=now_iso(),
            step_id=step_id,
            metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata is not None else None,
        )
        self.connection.execute(
            """
            INSERT INTO artifacts(
              artifact_id, run_id, step_id, artifact_type, name, uri, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.artifact_id,
                row.run_id,
                row.step_id,
                row.artifact_type,
                row.name,
                row.uri,
                row.metadata_json,
                row.created_at,
            ),
        )
        return row

    def list_for_run(self, run_id: str) -> list[ArtifactRow]:
        rows = self.connection.execute(
            """
            SELECT artifact_id, run_id, step_id, artifact_type, name, uri, metadata_json, created_at
            FROM artifacts
            WHERE run_id = ?
            ORDER BY created_at ASC, artifact_id ASC
            """,
            (run_id,),
        ).fetchall()
        return [_row_from_record(record) for record in rows]

    def delete_for_run_ids(self, run_ids: list[str]) -> None:
        if not run_ids:
            return
        placeholders = ", ".join("?" for _ in run_ids)
        self.connection.execute(
            f"""
            DELETE FROM artifacts
            WHERE run_id IN ({placeholders})
            """,
            tuple(run_ids),
        )


def _row_from_record(record: sqlite3.Row) -> ArtifactRow:
    return ArtifactRow(
        artifact_id=str(record["artifact_id"]),
        run_id=str(record["run_id"]),
        artifact_type=str(record["artifact_type"]),
        name=str(record["name"]),
        uri=str(record["uri"]),
        created_at=str(record["created_at"]),
        step_id=str(record["step_id"]) if record["step_id"] is not None else None,
        metadata_json=str(record["metadata_json"]) if record["metadata_json"] is not None else None,
    )
