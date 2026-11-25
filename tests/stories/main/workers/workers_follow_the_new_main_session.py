from journal.features.reviewing.reviewing_nudges import ReviewingNudges
from journal.features.tasks.tasks_nudges import TasksNudges
from journal.features.workers.states.orchestrating import Orchestrating
from journal.features.workers.workers_nudges import WorkersNudges
from journal.features.workers.workers_options import ORCHESTRATOR_MODE, WorkersOptions
from journal.support.agent_role import AgentRole
from tests.stories.builder.story_marks import setting, story
from tests.stories.fixtures.main.orchestrator_worker import OrchestratorWorker
from tests.stories.fixtures.main.orchestrator_worker_delivered import OrchestratorWorkerDelivered
from tests.stories.fixtures.reviewer.reviewer_at_work import ReviewerAtWork

NEWS_SECONDS = 300
# a clock tick, past the five seconds the journal's clock waits between two
TICK_SECONDS = 5


@story(OrchestratorWorker, mode=ORCHESTRATOR_MODE, subject=AgentRole.MAIN)
def test_after_a_restart_main_is_told_at_once_when_a_worker_from_the_last_session_clocks_out(story):
    story.second_session_starts()
    story.agent_proves(story.agents.workers.first(), 1, "parser.py:12, test_reads passes")
    story.agent_proves(story.agents.workers.first(), 2, "parser.py:30, test_names passes")
    result = story.agent_clocks_out(story.agents.workers.first(), "the parser is done")
    result.expect_agent_told(story.agents.subject, WorkersNudges.WORK_READY)
    story.expect_stack(story.agents.subject, Orchestrating)


@story(OrchestratorWorkerDelivered, mode=ORCHESTRATOR_MODE, subject=AgentRole.MAIN)
@setting(WorkersOptions.DIGEST_SECONDS, NEWS_SECONDS)
def test_after_a_restart_the_news_line_names_the_clocked_out_worker_from_the_last_session_as_needing_main(story):
    story.second_session_starts()
    result = story.clock_ticks(TICK_SECONDS)
    result.expect_agent_told(story.agents.subject, WorkersNudges.WORKER_NEWS, needs=f"worker {story.agents.workers.first()} ready")
    story.expect_stack(story.agents.subject, Orchestrating)


@story(ReviewerAtWork, mode=ORCHESTRATOR_MODE, subject=AgentRole.MAIN)
def test_after_a_restart_main_is_told_its_reviewed_worker_from_the_last_session_waits_on_it(story):
    story.second_session_starts()
    result = story.agent_runs(story.agents.reviewers.first(), "review record '1 passed. 2 undecided: the grammar file is missing.'")
    result.expect_agent_told(story.agents.subject, ReviewingNudges.REVIEW_UNDECIDED)
    story.expect_stack(story.agents.subject, Orchestrating)


@story(OrchestratorWorker, mode=ORCHESTRATOR_MODE, subject=AgentRole.MAIN)
@setting(WorkersOptions.DIGEST_SECONDS, NEWS_SECONDS)
def test_after_a_restart_a_stuck_main_is_told_at_once_when_a_worker_from_the_last_session_reports(story):
    story.second_session_starts()
    story.agent_runs(story.agents.subject, "stuck 'nothing to do until the workers report'")
    result = story.agent_runs(story.agents.workers.first(), f"worker report {story.agents.workers.first()} 'the grammar is ambiguous'")
    result.expect_agent_told(story.agents.subject, TasksNudges.WAIT_END)
    story.expect_stack(story.agents.subject, Orchestrating)
