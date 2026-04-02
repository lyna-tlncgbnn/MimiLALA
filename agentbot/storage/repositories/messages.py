"""Transcript message repository."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbot.storage.common import new_prefixed_id, now_iso
from agentbot.storage.models import MessageRow


class MessageRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(
        self,
        *,
        conversation_id: str,
        role: str,
        phase: str,
        visibility: str,
        content: Any,
        text_preview: str,
        run_id: str | None = None,
        message_id: str | None = None,
        created_at: str | None = None,
    ) -> MessageRow:
        row = MessageRow(
            message_id=message_id or new_prefixed_id("msg"),
            conversation_id=conversation_id,
            run_id=run_id,
            role=role,
            phase=phase,
            visibility=visibility,
            content_json=json.dumps(content, ensure_ascii=False),
            text_preview=text_preview,
            created_at=created_at or now_iso(),
        )
        self.connection.execute(
            """
            INSERT INTO messages(
              message_id, conversation_id, run_id, role, phase, visibility,
              content_json, text_preview, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.message_id,
                row.conversation_id,
                row.run_id,
                row.role,
                row.phase,
                row.visibility,
                row.content_json,
                row.text_preview,
                row.created_at,
            ),
        )
        return row

    def list_for_conversation(self, conversation_id: str, *, visible_only: bool = True) -> list[MessageRow]:
        if visible_only:
            rows = self.connection.execute(
                """
                SELECT message_id, conversation_id, run_id, role, phase, visibility,
                       content_json, text_preview, created_at
                FROM messages
                WHERE conversation_id = ? AND visibility = 'visible'
                ORDER BY created_at ASC, message_id ASC
                """,
                (conversation_id,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT message_id, conversation_id, run_id, role, phase, visibility,
                       content_json, text_preview, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC, message_id ASC
                """,
                (conversation_id,),
            ).fetchall()
        return [_row_from_record(record) for record in rows]

    def delete_for_conversation(self, conversation_id: str) -> None:
        self.connection.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )


def _row_from_record(record: sqlite3.Row) -> MessageRow:
    return MessageRow(
        message_id=str(record["message_id"]),
        conversation_id=str(record["conversation_id"]),
        run_id=str(record["run_id"]) if record["run_id"] is not None else None,
        role=str(record["role"]),
        phase=str(record["phase"]),
        visibility=str(record["visibility"]),
        content_json=str(record["content_json"]),
        text_preview=str(record["text_preview"]),
        created_at=str(record["created_at"]),
    )
