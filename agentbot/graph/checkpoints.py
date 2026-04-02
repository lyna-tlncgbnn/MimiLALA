"""Helpers for LangGraph SQLite checkpoint persistence."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.sqlite import SqliteSaver

from agentbot.storage.paths import checkpoints_path


@contextmanager
def sqlite_checkpointer() -> Iterator[SqliteSaver]:
    path = checkpoints_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(path)) as saver:
        saver.setup()
        yield saver


def thread_config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


def thread_has_checkpoints(checkpointer: SqliteSaver, thread_id: str) -> bool:
    return checkpointer.get_tuple(thread_config(thread_id)) is not None
