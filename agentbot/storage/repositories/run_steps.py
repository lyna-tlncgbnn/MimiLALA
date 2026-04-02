"""Run step repository."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbot.storage.common import new_prefixed_id, now_iso
from agentbot.storage.models import RunStepRow


class RunStepRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(
        self,
        *,
        run_id: str,
        step_type: str,
        title: str,
        status: str,
        display_mode: str,
        sort_order: int,
        parent_step_id: str | None = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        input_payload: Any = None,
        output_payload: Any = None,
        summary_text: str | None = None,
        started_at: str | None = None,
    ) -> RunStepRow:
        row = RunStepRow(
            step_id=new_prefixed_id("step"),
            run_id=run_id,
            step_type=step_type,
            title=title,
            status=status,
            display_mode=display_mode,
            sort_order=sort_order,
            started_at=started_at or now_iso(),
            parent_step_id=parent_step_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            input_json=_dump_json(input_payload),
            output_json=_dump_json(output_payload),
            summary_text=summary_text,
        )
        self.connection.execute(
            """
            INSERT INTO run_steps(
              step_id, run_id, parent_step_id, step_type, title, status,
              tool_name, tool_call_id, input_json, output_json, summary_text,
              display_mode, sort_order, started_at, ended_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.step_id,
                row.run_id,
                row.parent_step_id,
                row.step_type,
                row.title,
                row.status,
                row.tool_name,
                row.tool_call_id,
                row.input_json,
                row.output_json,
                row.summary_text,
                row.display_mode,
                row.sort_order,
                row.started_at,
                row.ended_at,
            ),
        )
        return row

    def list_for_run(self, run_id: str) -> list[RunStepRow]:
        rows = self.connection.execute(
            """
            SELECT step_id, run_id, parent_step_id, step_type, title, status,
                   tool_name, tool_call_id, input_json, output_json, summary_text,
                   display_mode, sort_order, started_at, ended_at
            FROM run_steps
            WHERE run_id = ?
            ORDER BY sort_order ASC, started_at ASC, step_id ASC
            """,
            (run_id,),
        ).fetchall()
        return [_row_from_record(record) for record in rows]

    def get(self, step_id: str) -> RunStepRow | None:
        record = self.connection.execute(
            """
            SELECT step_id, run_id, parent_step_id, step_type, title, status,
                   tool_name, tool_call_id, input_json, output_json, summary_text,
                   display_mode, sort_order, started_at, ended_at
            FROM run_steps
            WHERE step_id = ?
            """,
            (step_id,),
        ).fetchone()
        return _row_from_record(record) if record else None

    def update_status(
        self,
        step_id: str,
        *,
        status: str,
        output_payload: Any = None,
        summary_text: str | None = None,
        ended_at: str | None = None,
    ) -> RunStepRow | None:
        current = self.connection.execute(
            """
            SELECT step_id, run_id, parent_step_id, step_type, title, status,
                   tool_name, tool_call_id, input_json, output_json, summary_text,
                   display_mode, sort_order, started_at, ended_at
            FROM run_steps
            WHERE step_id = ?
            """,
            (step_id,),
        ).fetchone()
        if current is None:
            return None
        self.connection.execute(
            """
            UPDATE run_steps
            SET status = ?,
                output_json = ?,
                summary_text = ?,
                ended_at = ?
            WHERE step_id = ?
            """,
            (
                status,
                _dump_json(output_payload) if output_payload is not None else current["output_json"],
                summary_text if summary_text is not None else current["summary_text"],
                ended_at or now_iso(),
                step_id,
            ),
        )
        updated = self.connection.execute(
            """
            SELECT step_id, run_id, parent_step_id, step_type, title, status,
                   tool_name, tool_call_id, input_json, output_json, summary_text,
                   display_mode, sort_order, started_at, ended_at
            FROM run_steps
            WHERE step_id = ?
            """,
            (step_id,),
        ).fetchone()
        return _row_from_record(updated) if updated else None

    def delete_for_run_ids(self, run_ids: list[str]) -> None:
        if not run_ids:
            return
        placeholders = ", ".join("?" for _ in run_ids)
        self.connection.execute(
            f"""
            DELETE FROM run_steps
            WHERE run_id IN ({placeholders})
            """,
            tuple(run_ids),
        )


def _dump_json(payload: Any) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False)


def _row_from_record(record: sqlite3.Row) -> RunStepRow:
    return RunStepRow(
        step_id=str(record["step_id"]),
        run_id=str(record["run_id"]),
        step_type=str(record["step_type"]),
        title=str(record["title"]),
        status=str(record["status"]),
        display_mode=str(record["display_mode"]),
        sort_order=int(record["sort_order"]),
        started_at=str(record["started_at"]),
        parent_step_id=str(record["parent_step_id"]) if record["parent_step_id"] is not None else None,
        tool_name=str(record["tool_name"]) if record["tool_name"] is not None else None,
        tool_call_id=str(record["tool_call_id"]) if record["tool_call_id"] is not None else None,
        input_json=str(record["input_json"]) if record["input_json"] is not None else None,
        output_json=str(record["output_json"]) if record["output_json"] is not None else None,
        summary_text=str(record["summary_text"]) if record["summary_text"] is not None else None,
        ended_at=str(record["ended_at"]) if record["ended_at"] is not None else None,
    )
