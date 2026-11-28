from journal.support.timeout import Timeout
from journal.support.card_outcome import CardOutcome
import time

from journal.support.masks import Masks
from journal.chat.moment_cards import MomentCards
from journal.events.agent.ticked import Ticked
from journal.events.agent_listener import AgentListener
from journal.support.card_type import CardType
from journal.support.time_source import TimeSource

ALARM_INTERVAL_SECONDS = 600.0


class LeakAlarm(AgentListener[Ticked]):
    """A secret's value that reached a write was masked there; at the next tick the user is shown which, so the leak is seen and not only stopped. A stored hidden value too weak to mask is shown once as well, so it is replaced."""

    def __init__(self, masks: Masks, cards: MomentCards, time_source: TimeSource) -> None:
        self.time_source = time_source
        self.masks, self.cards = masks, cards
        self._said_at = 0.0
        self._weak_said: tuple[str, ...] = ()

    def handle(self, event: Ticked) -> None:
        self.report_weak(event)
        if not self.masks.leaks or not Timeout.seconds(ALARM_INTERVAL_SECONDS).started(self._said_at).is_elapsed(self.time_source.seconds()):
            return
        variables = sorted({variable for variable, _ in self.masks.leaks})
        self.masks.leaks.clear()
        self._said_at = self.time_source.seconds()
        self.cards.show(event.environment_id, event.session, "A secret was hidden before it could be saved", ', '.join(variables), shows=CardType.FAULTS, outcome=CardOutcome.WARNED)

    def report_weak(self, event: Ticked) -> None:
        self.masks.current()
        if not self.masks.weak or self.masks.weak == self._weak_said:
            return
        self._weak_said = self.masks.weak
        self.cards.show(event.environment_id, event.session, "A stored secret is a common word or shorter than eight characters, so it is never masked: give it a real value", ', '.join(self.masks.weak), shows=CardType.FAULTS, outcome=CardOutcome.WARNED)
