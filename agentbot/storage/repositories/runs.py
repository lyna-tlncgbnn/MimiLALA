"""Run repository."""

from __future__ import annotations

import sqlite3

from agentbot.storage.common import new_prefixed_id, now_iso
from agentbot.storage.models import RunRow


class RunRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(
        self,
        *,
        conversation_id: str,
        thread_id: str,
        status: str = "queued",
        workflow_name: str | None = None,
        user_message_id: str | None = None,
        run_id: str | None = None,
        started_at: str | None = None,
    ) -> RunRow:
        row = RunRow(
            run_id=run_id or new_prefixed_id("run"),
            conversation_id=conversation_id,
            thread_id=thread_id,
            status=status,
            started_at=started_at or now_iso(),
            user_message_id=user_message_id,
            workflow_name=workflow_name,
        )
        self.connection.execute(
            """
            INSERT INTO runs(
              run_id, conversation_id, thread_id, user_message_id, final_message_id,
              workflow_name, status, started_at, ended_at, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.run_id,
                row.conversation_id,
                row.thread_id,
                row.user_message_id,
                row.final_message_id,
                row.workflow_name,
                row.status,
                row.started_at,
                row.ended_at,
                row.error_message,
            ),
        )
        return row

    def get(self, run_id: str) -> RunRow | None:
        record = self.connection.execute(
            """
            SELECT runs.run_id,
                   runs.conversation_id,
                   runs.thread_id,
                   runs.user_message_id,
                   runs.final_message_id,
                   runs.workflow_name,
                   runs.status,
                   runs.started_at,
                   runs.ended_at,
                   runs.error_message,
                   COUNT(run_steps.step_id) AS step_count,
                   SUM(CASE WHEN run_steps.display_mode != 'hidden' THEN 1 ELSE 0 END) AS visible_step_count
            FROM runs
            LEFT JOIN run_steps ON run_steps.run_id = runs.run_id
            WHERE runs.run_id = ?
            GROUP BY runs.run_id, runs.conversation_id, runs.thread_id, runs.user_message_id,
                     runs.final_message_id, runs.workflow_name, runs.status, runs.started_at,
                     runs.ended_at, runs.error_message
            """,
            (run_id,),
        ).fetchone()
        return _row_from_record(record) if record else None

    def list_for_conversation(self, conversation_id: str) -> list[RunRow]:
        rows = self.connection.execute(
            """
            SELECT runs.run_id,
                   runs.conversation_id,
                   runs.thread_id,
                   runs.user_message_id,
                   runs.final_message_id,
                   runs.workflow_name,
                   runs.status,
                   runs.started_at,
                   runs.ended_at,
                   runs.error_message,
                   COUNT(run_steps.step_id) AS step_count,
                   SUM(CASE WHEN run_steps.display_mode != 'hidden' THEN 1 ELSE 0 END) AS visible_step_count
            FROM runs
            LEFT JOIN run_steps ON run_steps.run_id = runs.run_id
            WHERE runs.conversation_id = ?
            GROUP BY runs.run_id, runs.conversation_id, runs.thread_id, runs.user_message_id,
                     runs.final_message_id, runs.workflow_name, runs.status, runs.started_at,
                     runs.ended_at, runs.error_message
            ORDER BY runs.started_at DESC, runs.run_id DESC
            """,
            (conversation_id,),
        ).fetchall()
        return [_row_from_record(record) for record in rows]

    def get_latest_for_conversation(self, conversation_id: str) -> RunRow | None:
        record = self.connection.execute(
            """
            SELECT runs.run_id,
                   runs.conversation_id,
                   runs.thread_id,
                   runs.user_message_id,
                   runs.final_message_id,
                   runs.workflow_name,
                   runs.status,
                   runs.started_at,
                   runs.ended_at,
                   runs.error_message,
                   COUNT(run_steps.step_id) AS step_count,
                   SUM(CASE WHEN run_steps.display_mode != 'hidden' THEN 1 ELSE 0 END) AS visible_step_count
            FROM runs
            LEFT JOIN run_steps ON run_steps.run_id = runs.run_id
            WHERE runs.conversation_id = ?
            GROUP BY runs.run_id, runs.conversation_id, runs.thread_id, runs.user_message_id,
                     runs.final_message_id, runs.workflow_name, runs.status, runs.started_at,
                     runs.ended_at, runs.error_message
            ORDER BY runs.started_at DESC, runs.run_id DESC
            LIMIT 1
            """,
            (conversation_id,),
        ).fetchone()
        return _row_from_record(record) if record else None

    def update_status(
        self,
        run_id: str,
        *,
        status: str,
        final_message_id: str | None = None,
        error_message: str | None = None,
        ended_at: str | None = None,
    ) -> RunRow | None:
        current = self.get(run_id)
        if current is None:
            return None
        self.connection.execute(
            """
            UPDATE runs
            SET status = ?,
                final_message_id = ?,
                error_message = ?,
                ended_at = ?
            WHERE run_id = ?
            """,
            (
                status,
                final_message_id if final_message_id is not None else current.final_message_id,
                error_message if error_message is not None else current.error_message,
                ended_at or now_iso(),
                run_id,
            ),
        )
        return self.get(run_id)

    def delete_for_conversation(self, conversation_id: str) -> None:
        self.connection.execute(
            """
            DELETE FROM runs
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )


def _row_from_record(record: sqlite3.Row) -> RunRow:
    step_count = int(record["step_count"]) if record["step_count"] is not None else 0
    visible_step_count = int(record["visible_step_count"]) if record["visible_step_count"] is not None else 0
    return RunRow(
        run_id=str(record["run_id"]),
        conversation_id=str(record["conversation_id"]),
        thread_id=str(record["thread_id"]),
        status=str(record["status"]),
        started_at=str(record["started_at"]),
        user_message_id=str(record["user_message_id"]) if record["user_message_id"] is not None else None,
        final_message_id=str(record["final_message_id"]) if record["final_message_id"] is not None else None,
        workflow_name=str(record["workflow_name"]) if record["workflow_name"] is not None else None,
        ended_at=str(record["ended_at"]) if record["ended_at"] is not None else None,
        error_message=str(record["error_message"]) if record["error_message"] is not None else None,
        step_count=step_count,
        visible_step_count=visible_step_count,
        has_execution=visible_step_count > 0,
    )
