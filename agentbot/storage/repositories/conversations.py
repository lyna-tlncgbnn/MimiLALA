"""Conversation repository for the redesigned storage layer."""

from __future__ import annotations

import sqlite3

from agentbot.storage.common import new_prefixed_id, now_iso
from agentbot.storage.models import ConversationRow


class ConversationRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, title: str) -> ConversationRow:
        timestamp = now_iso()
        row = ConversationRow(
            conversation_id=new_prefixed_id("conv"),
            title=title,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.connection.execute(
            """
            INSERT INTO conversations(conversation_id, title, created_at, updated_at, archived_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (row.conversation_id, row.title, row.created_at, row.updated_at, row.archived_at),
        )
        return row

    def upsert(
        self,
        *,
        conversation_id: str,
        title: str,
        created_at: str,
        updated_at: str,
        archived_at: str | None = None,
    ) -> ConversationRow:
        self.connection.execute(
            """
            INSERT INTO conversations(conversation_id, title, created_at, updated_at, archived_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
              title = excluded.title,
              created_at = excluded.created_at,
              updated_at = excluded.updated_at,
              archived_at = excluded.archived_at
            """,
            (conversation_id, title, created_at, updated_at, archived_at),
        )
        row = self.get(conversation_id)
        if row is None:
            raise ValueError(f"Failed to upsert conversation: {conversation_id}")
        return row

    def get(self, conversation_id: str) -> ConversationRow | None:
        record = self.connection.execute(
            """
            SELECT conversation_id, title, created_at, updated_at, archived_at
            FROM conversations
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
        return _row_from_record(record) if record else None

    def list_all(self) -> list[ConversationRow]:
        rows = self.connection.execute(
            """
            SELECT conversation_id, title, created_at, updated_at, archived_at
            FROM conversations
            ORDER BY updated_at DESC, created_at DESC, conversation_id DESC
            """
        ).fetchall()
        return [_row_from_record(record) for record in rows]

    def update_title(self, conversation_id: str, title: str) -> ConversationRow | None:
        updated_at = now_iso()
        cursor = self.connection.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE conversation_id = ?
            """,
            (title, updated_at, conversation_id),
        )
        if cursor.rowcount == 0:
            return None
        return self.get(conversation_id)

    def touch(self, conversation_id: str, updated_at: str | None = None) -> None:
        self.connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE conversation_id = ?
            """,
            (updated_at or now_iso(), conversation_id),
        )

    def delete(self, conversation_id: str) -> None:
        self.connection.execute(
            """
            DELETE FROM conversations
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )


def _row_from_record(record: sqlite3.Row) -> ConversationRow:
    return ConversationRow(
        conversation_id=str(record["conversation_id"]),
        title=str(record["title"]),
        created_at=str(record["created_at"]),
        updated_at=str(record["updated_at"]),
        archived_at=str(record["archived_at"]) if record["archived_at"] is not None else None,
    )
