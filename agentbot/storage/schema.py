"""SQLite schema bootstrap for the redesigned agent runtime."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

DDL_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS schema_metadata (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversations (
      conversation_id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      archived_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY,
      conversation_id TEXT NOT NULL,
      thread_id TEXT NOT NULL,
      user_message_id TEXT,
      final_message_id TEXT,
      workflow_name TEXT,
      status TEXT NOT NULL,
      started_at TEXT NOT NULL,
      ended_at TEXT,
      error_message TEXT,
      FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
      message_id TEXT PRIMARY KEY,
      conversation_id TEXT NOT NULL,
      run_id TEXT,
      role TEXT NOT NULL,
      phase TEXT NOT NULL,
      visibility TEXT NOT NULL,
      content_json TEXT NOT NULL,
      text_preview TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
      FOREIGN KEY (run_id) REFERENCES runs(run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_steps (
      step_id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      parent_step_id TEXT,
      step_type TEXT NOT NULL,
      title TEXT NOT NULL,
      status TEXT NOT NULL,
      tool_name TEXT,
      tool_call_id TEXT,
      input_json TEXT,
      output_json TEXT,
      summary_text TEXT,
      display_mode TEXT NOT NULL,
      sort_order INTEGER NOT NULL,
      started_at TEXT NOT NULL,
      ended_at TEXT,
      FOREIGN KEY (run_id) REFERENCES runs(run_id),
      FOREIGN KEY (parent_step_id) REFERENCES run_steps(step_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
      artifact_id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      step_id TEXT,
      artifact_type TEXT NOT NULL,
      name TEXT NOT NULL,
      uri TEXT NOT NULL,
      metadata_json TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY (run_id) REFERENCES runs(run_id),
      FOREIGN KEY (step_id) REFERENCES run_steps(step_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
      ON conversations(updated_at DESC, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_conversation_created_at
      ON messages(conversation_id, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_run_id
      ON messages(run_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_runs_conversation_started_at
      ON runs(conversation_id, started_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_runs_thread_id
      ON runs(thread_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_run_steps_run_sort_order
      ON run_steps(run_id, sort_order)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_run_steps_tool_call_id
      ON run_steps(tool_call_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_artifacts_run_id
      ON artifacts(run_id, created_at)
    """,
)


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    for statement in DDL_STATEMENTS:
        connection.execute(statement)
    connection.execute(
        """
        INSERT INTO schema_metadata(key, value)
        VALUES ('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (str(SCHEMA_VERSION),),
    )
    connection.commit()
