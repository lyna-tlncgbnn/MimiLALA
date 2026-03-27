"""Minimal CLI entrypoint for the current learning stages."""

from __future__ import annotations

import sys

from agentbot.app.runner import AgentBotError, run_once

EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit"}
ASSISTANT_LABEL = "AgentBot"


def _read_single_user_text(argv: list[str]) -> str:
    return " ".join(argv[1:]).strip()


def _run_interactive_loop() -> int:
    while True:
        try:
            user_text = input("You: ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 0

        if not user_text:
            continue
        if user_text.lower() in EXIT_COMMANDS:
            return 0

        try:
            _print_assistant_reply(run_once(user_text))
        except AgentBotError as exc:
            print(f"Error: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv
    if len(args) > 1:
        try:
            user_text = _read_single_user_text(args)
            if not user_text:
                print("Error: Please provide a message.", file=sys.stderr)
                return 1
            _print_assistant_reply(run_once(user_text))
            return 0
        except AgentBotError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    return _run_interactive_loop()


def _print_assistant_reply(reply: str) -> None:
    print(f"{ASSISTANT_LABEL}:")
    print(reply)
