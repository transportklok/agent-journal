from journal.features.tasks.states.external_wait import ExternalWait
from journal.features.workers.states.orchestrating import Orchestrating
from journal.features.workers.workers_nudges import WorkersNudges
from journal.features.workers.workers_options import ORCHESTRATOR_MODE
from journal.models.worker_state import WorkerState
from journal.support.agent_role import AgentRole
from tests.stories.builder.story_marks import story
from tests.stories.fixtures.main.orchestrator_worker_ended import OrchestratorWorkerEnded


@story(OrchestratorWorkerEnded, mode=ORCHESTRATOR_MODE, subject=AgentRole.MAIN)
def test_a_worker_that_ended_without_clocking_out_ten_minutes_ago_is_named_to_the_orchestrator_on_its_tick(story):
    """On the hosted journal worker 3469 ended without clocking out and was named once; the orchestrator was replaced by
    restarts and nobody resent it for 17 hours while 29 blocked tasks waited on its task (24-25 Nov)."""
    story.time_travel(minutes=11)
    result = story.agent_is_quiet_for(story.agents.subject, 1)
    result.expect_agent_told(story.agents.subject, WorkersNudges.ENDED_WORK_WAITS)
    story.expect_stack(story.agents.subject, Orchestrating)


@story(OrchestratorWorkerEnded, mode=ORCHESTRATOR_MODE, subject=AgentRole.MAIN)
def test_a_worker_that_ended_without_clocking_out_minutes_ago_is_not_named_yet(story):
    result = story.agent_is_quiet_for(story.agents.subject, 1)
    result.expect_agent_not_told(story.agents.subject, WorkersNudges.ENDED_WORK_WAITS)
    story.expect_stack(story.agents.subject, Orchestrating)


@story(OrchestratorWorkerEnded, mode=ORCHESTRATOR_MODE, subject=AgentRole.MAIN)
def test_a_worker_of_another_dispatcher_that_ended_without_clocking_out_is_not_named(story):
    story.worker_belongs_to_another_session(story.agents.workers.first())
    story.time_travel(minutes=11)
    result = story.agent_is_quiet_for(story.agents.subject, 1)
    result.expect_agent_not_told(story.agents.subject, WorkersNudges.ENDED_WORK_WAITS)
    story.expect_stack(story.agents.subject, Orchestrating)


@story(OrchestratorWorkerEnded, mode=ORCHESTRATOR_MODE, subject=AgentRole.MAIN)
def test_a_worker_that_ended_without_clocking_out_and_was_resent_is_not_named(story):
    story.agent_runs(story.agents.subject, f"worker send {story.agents.workers.first()} 'run the tests and clock out'")
    story.expect_worker(story.agents.workers.first(), state=WorkerState.DISPATCHED)
    story.time_travel(minutes=11)
    result = story.agent_is_quiet_for(story.agents.subject, 1)
    result.expect_agent_not_told(story.agents.subject, WorkersNudges.ENDED_WORK_WAITS)
    story.expect_stack(story.agents.subject, Orchestrating, ExternalWait)
