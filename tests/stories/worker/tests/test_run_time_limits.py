from journal.engine.states.void import Void
from journal.features.workers.states.working_task import WorkingTask
from journal.features.workers.workers_nudges import WorkersNudges
from journal.features.workers.workers_options import BUILDER_MODE, WorkersOptions
from journal.support.agent_role import AgentRole
from tests.stories.builder.story_marks import story
from tests.stories.fixtures.worker.short_test_limit_worker import ShortTestLimitWorker
from tests.stories.fixtures.worker.worker_holding_a_test_turn import WorkerHoldingATestTurn

STOP_LINE = "journal: this test run was stopped"
SCRIPT = "#!/bin/sh\nif [ \"$1\" = turn_story.py ]; then sleep 2; else sleep 3; fi\necho '1 passed'\n"
ENDLESS_SCRIPT = "#!/bin/sh\nsleep 30\necho '1 passed'\n"


@story(ShortTestLimitWorker, mode=BUILDER_MODE, subject=AgentRole.WORKER)
def test_the_time_limit_of_a_turn_whose_run_moved_to_the_background_leaves_the_later_clock_out_run_to_pass(story):
    story.agent_proves(story.agents.subject, 1, "parser.py:12, test_reads passes")
    story.agent_proves(story.agents.subject, 2, "parser.py:30, test_names passes")
    story.project_script_holding("run_tests.sh", SCRIPT)
    story.agent_backgrounds_test_turn(story.agents.subject, "turn_story.py")
    story.user_sets(WorkersOptions.TEST_RUN_MINUTES, 10)
    story.agent_runs(story.agents.subject, "clock-out 'the parser is done' --tests passing_story.py")
    story.last_step.expect_command_passed()
    story.last_step.expect_agent_told(story.agents.main, WorkersNudges.WORK_READY)
    story.expect_no_output_line(story.newest_output(), STOP_LINE)
    story.expect_stack(story.agents.subject, Void)


@story(ShortTestLimitWorker, mode=BUILDER_MODE, subject=AgentRole.WORKER)
def test_a_test_run_in_the_background_is_stopped_at_its_time_limit_and_a_command_run_after_it_in_its_folder_is_not(story):
    story.project_script_holding("run_tests.sh", ENDLESS_SCRIPT)
    tests = story.agent_backgrounds_test_turn(story.agents.subject, "turn_story.py")
    migration = story.agent_has_a_background_run_printing(story.agents.main, "./scripts/migrate.sh", "migrating")
    story.test_run_stops(tests)
    story.expect_output_line(tests, STOP_LINE)
    story.expect_no_output_line(migration, STOP_LINE)
    story.expect_stack(story.agents.subject, Void, WorkingTask)


@story(WorkerHoldingATestTurn, mode=BUILDER_MODE, subject=AgentRole.WORKER)
def test_a_worker_stopped_with_a_test_turn_open_leaves_another_agents_command_in_its_folder_running(story):
    migration = story.agent_has_a_background_run_printing(story.agents.main, "./scripts/migrate.sh", "migrating")
    story.agent_runs(story.agents.main, f"worker stop {story.agents.subject}")
    story.expect_no_test_turn_open()
    story.expect_no_output_line(migration, STOP_LINE)
    story.expect_stack(story.agents.subject, Void, WorkingTask)
