"""Run query use cases."""

from __future__ import annotations

from dataclasses import dataclass

from agentbot.storage.db import AgentDatabase
from agentbot.storage.models import ArtifactRow, RunRow, RunStepRow
from agentbot.storage.repositories import ArtifactRepository, RunRepository, RunStepRepository


@dataclass(slots=True)
class RunStepsResult:
    run: RunRow
    steps: list[RunStepRow]


@dataclass(slots=True)
class RunArtifactsResult:
    run: RunRow
    artifacts: list[ArtifactRow]


class RunQueries:
    """Read run-oriented data through explicit query use cases."""

    def __init__(self, database: AgentDatabase | None = None):
        self.database = database or AgentDatabase()

    def get_run(self, run_id: str) -> RunRow:
        self.database.initialize()
        with self.database.connect() as connection:
            run = RunRepository(connection).get(run_id)
            if run is None:
                raise FileNotFoundError(f"Run not found: {run_id}")
            return run

    def list_for_conversation(self, conversation_id: str) -> list[RunRow]:
        self.database.initialize()
        with self.database.connect() as connection:
            return RunRepository(connection).list_for_conversation(conversation_id)

    def get_latest_for_conversation(self, conversation_id: str) -> RunRow:
        self.database.initialize()
        with self.database.connect() as connection:
            run = RunRepository(connection).get_latest_for_conversation(conversation_id)
            if run is None:
                raise RuntimeError(f"No run persisted for conversation: {conversation_id}")
            return run

    def get_run_steps(self, run_id: str) -> RunStepsResult:
        self.database.initialize()
        with self.database.connect() as connection:
            run_repo = RunRepository(connection)
            step_repo = RunStepRepository(connection)

            run = run_repo.get(run_id)
            if run is None:
                raise FileNotFoundError(f"Run not found: {run_id}")

            return RunStepsResult(run=run, steps=step_repo.list_for_run(run_id))

    def get_run_artifacts(self, run_id: str) -> RunArtifactsResult:
        self.database.initialize()
        with self.database.connect() as connection:
            run_repo = RunRepository(connection)
            artifact_repo = ArtifactRepository(connection)

            run = run_repo.get(run_id)
            if run is None:
                raise FileNotFoundError(f"Run not found: {run_id}")

            return RunArtifactsResult(run=run, artifacts=artifact_repo.list_for_run(run_id))
