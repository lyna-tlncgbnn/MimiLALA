"""Minimal CLI entrypoint for Phase 1."""

from __future__ import annotations

import sys

from agentbot.app.runner import AgentBotError, run_once


def _read_user_text(argv: list[str]) -> str:
    if len(argv) > 1:
        return " ".join(argv[1:]).strip()
    return input("You: ").strip()


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv
    try:
        user_text = _read_user_text(args)
        if not user_text:
            print("Error: Please provide a message.", file=sys.stderr)
            return 1
        print(run_once(user_text))
        return 0
    except AgentBotError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

