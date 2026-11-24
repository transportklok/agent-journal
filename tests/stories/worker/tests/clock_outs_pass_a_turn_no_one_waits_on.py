from journal.engine.states.void import Void
from journal.features.workers.workers_nudges import WorkersNudges
from journal.features.workers.workers_options import BUILDER_MODE, WorkersOptions
from journal.models.worker_state import WorkerState
from journal.support.agent_role import AgentRole
from tests.stories.builder.story_marks import setting, story
from tests.stories.fixtures.worker.worker_holding_a_test_turn import WorkerHoldingATestTurn

PASSING_SCRIPT = "#!/bin/sh\necho '1 passed'\n"


@story(WorkerHoldingATestTurn, mode=BUILDER_MODE, subject=AgentRole.WORKER)
@setting(WorkersOptions.TEST_COMMAND, "./run_tests.sh")
@setting(WorkersOptions.CLOCK_OUT_FOREGROUND_SECONDS, 0)
def test_a_clock_out_runs_its_tests_past_an_earlier_waiting_turn_whose_caller_is_gone(story):
    story.project_script_holding("run_tests.sh", PASSING_SCRIPT)
    story.test_turn_left_waiting_by_a_gone_caller(story.agents.subject, "elsewhere_story.py")
    story.worker_test_run_ends_after(story.agents.subject, 0.5)
    result = story.agent_runs(story.agents.subject, "clock-out 'the parser is done' --tests passing_story.py")
    result.expect_command_passed()
    result = story.worker_clock_out_ends_in_the_journal(story.agents.subject)
    result.expect_agent_told(story.agents.main, WorkersNudges.WORK_READY)
    story.expect_worker(story.agents.subject, state=WorkerState.DELIVERED)
    story.expect_stack(story.agents.subject, Void)
