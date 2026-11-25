from journal.events.listener import Listener
from journal.events.rows.main_session_replaced import MainSessionReplaced
from journal.repositories.workers import Workers
from journal.support.actor import Actor


class DispatcherSessionFollow(Listener[MainSessionReplaced]):
    """The workers an earlier session of the main agent sent, and that are not done, are the new session's as soon as it starts."""

    def __init__(self, workers: Workers) -> None:
        self.workers = workers

    def handle(self, event: MainSessionReplaced) -> None:
        for worker in self.workers.unfinished_of_dispatchers(event.earlier_sessions):
            self.workers.save(worker.dispatched_by(event.agent_session), Actor.system())
