from dataclasses import dataclass

from journal.events.rows.row_event import RowEvent


@dataclass(frozen=True, kw_only=True)
class MainSessionReplaced(RowEvent):
    """The main agent's row went on in a new session, so what its earlier sessions sent is the new session's."""

    agent_session: str
    earlier_sessions: tuple[str, ...]
