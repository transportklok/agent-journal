from journal.engine.states.compacting import Compacting
from journal.features.messages.messages_nudges import MessagesNudges
from journal.features.tasks.states.ready import Ready
from journal.features.tasks.states.working import Working
from journal.features.workers.workers_options import BUILDER_MODE
from journal.support.agent_role import AgentRole
from journal.engine.clock import Clock
from tests.stories.builder.story_marks import story
from tests.stories.fixtures.main.compacting_task import CompactingTask
from tests.stories.fixtures.main.working_agent import WorkingAgent


@story(WorkingAgent, mode=BUILDER_MODE, subject=AgentRole.MAIN)
def test_a_line_for_an_idle_agent_whose_compaction_was_overwritten_is_typed_after_the_next_tick(story):
    story.compaction_begins()
    story.a_stale_save_writes_back_the_stack(story.agents.subject, Ready)
    story.agent_stops(story.agents.subject)
    story.clock_ticks(Clock.interval_seconds)
    message = story.user_sends_message("is the footer done?")
    story.expect_typed(MessagesNudges.NEW_MESSAGE.create(n=message))
    story.expect_stack(story.agents.subject, Ready)


@story(CompactingTask, mode=BUILDER_MODE, subject=AgentRole.MAIN)
def test_a_tick_during_a_compaction_leaves_typing_off(story):
    story.clock_ticks(Clock.interval_seconds)
    story.user_sends_message("is the footer done?")
    story.expect_typed()
    story.expect_stack(story.agents.subject, Ready, Working, Compacting)
