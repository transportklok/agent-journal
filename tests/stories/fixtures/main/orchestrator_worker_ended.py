from journal.engine.states.ended import Ended
from journal.engine.states.void import Void
from journal.features.workers.states.working_task import WorkingTask
from journal.features.workers.states.orchestrating import Orchestrating
from journal.models.worker_state import WorkerState
from tests.stories.fixtures.main.orchestrator_worker import OrchestratorWorker
from tests.stories.fixtures.state_fixture import StateFixture


class OrchestratorWorkerEnded(StateFixture):
    """The orchestrator's worker ended its run without clocking out, was asked once by the journal to clock out and ended so again: story.agents.workers.first()."""

    stack = (Orchestrating,)

    parent = OrchestratorWorker

    def steps(self, story) -> None:
        story.worker_run_ends_mid_turn(story.agents.workers.first(), "waiting on the tests")
        story.worker_run_ends_mid_turn(story.agents.workers.first(), "still waiting on the tests")

    def expected(self, story) -> None:
        story.expect_worker(self.workers.first, state=WorkerState.UNFINISHED)
        story.expect_stack(story.agents.workers.first(), Void, WorkingTask, Ended)
