from journal.engine.states.void import Void
from journal.features.tasks.states.external_wait import ExternalWait
from journal.features.tasks.states.ready import Ready
from journal.features.workers.states.working_task import WorkingTask
from journal.features.workers.workers_options import WorkersOptions
from journal.support.foreground_option import FOREGROUND_OPTION
from tests.stories.fixtures.state_fixture import StateFixture
from tests.stories.fixtures.worker.working_worker import WorkingWorker


class ShortTestLimitWorker(StateFixture):
    """The working worker in a project whose test command is a script, whose runs move to the background after a second and are stopped after a few."""

    stack = (Ready, ExternalWait)

    parent = WorkingWorker

    def steps(self, story) -> None:
        story.user_sets(WorkersOptions.TEST_COMMAND, "./run_tests.sh")
        story.user_sets(WorkersOptions.TEST_RUN_MINUTES, 0.06)
        story.user_sets(FOREGROUND_OPTION, 1)

    def expected(self, story) -> None:
        story.expect_stack(story.agents.workers.first(), Void, WorkingTask)
