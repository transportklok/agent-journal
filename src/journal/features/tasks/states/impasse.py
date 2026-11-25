from dataclasses import dataclass

from journal.engine.states.wait import Wait
from journal.engine.support.settings import Settings
from journal.engine.support.transition import Transition
from journal.events.rows.row_resolved import RowResolved
from journal.events.rows.task_opened import TaskOpened
from journal.events.rows.task_reopened import TaskReopened
from journal.events.rows.worker_delivered import WorkerDelivered
from journal.events.rows.worker_mention import WorkerMention
from journal.events.rows.worker_queue_empty import WorkerQueueEmpty
from journal.events.rows.worker_reported import WorkerReported
from journal.events.rows.worker_review_undecided import WorkerReviewUndecided
from journal.features.tasks.tasks_nudges import TasksNudges


@dataclass(frozen=True)
class Impasse(Wait):
    """The agent reported it is stuck. Nothing is sent until it works again or the user writes: its own next tool use, a word from the user, a task opened again, a new open task, or a worker it sent that now waits on its decision pops it."""

    name = "stuck"
    title = "Stuck"
    reason: str = ""

    def wait_description(self) -> tuple[str, str]:
        return self.reason, ""

    def impasse_reason(self) -> str:
        return self.reason

    def on_task_reopened(self, event: TaskReopened, settings: Settings) -> Transition:
        return self.pop()

    def on_task_opened(self, event: TaskOpened, settings: Settings) -> Transition:
        return self.pop(TasksNudges.TASK_OPENED.create(n=event.row_id, title=event.title)) if event.is_users() else self.none()

    def on_worker_delivered(self, event: WorkerDelivered, settings: Settings) -> Transition:
        return self.worker_waits(event.worker, event)

    def on_worker_reported(self, event: WorkerReported, settings: Settings) -> Transition:
        return self.worker_waits(event.worker, event)

    def on_worker_review_undecided(self, event: WorkerReviewUndecided, settings: Settings) -> Transition:
        return self.worker_waits(event.worker, event)

    def on_worker_queue_empty(self, event: WorkerQueueEmpty, settings: Settings) -> Transition:
        return self.worker_waits(event.worker, event)

    def worker_waits(self, worker: WorkerMention, event: RowResolved) -> Transition:
        return self.none() if worker.is_other_dispatcher(event.session) else self.pop(TasksNudges.WAIT_END.create(outcome=event.outcome))
