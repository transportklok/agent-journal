import threading

from journal.engine.job import Job
from journal.engine.states_catalogue import StatesCatalogue
from journal.events.agent.ticked import Ticked
from journal.support.fault_log import FaultLog
from journal.events.clock_ticked import ClockTicked
from journal.events.bus import Bus
from journal.support.decision import Decision
from journal.models.agent import Agent
from journal.repositories.agents import Agents
from journal.repositories.scope import Scope
from journal.supervisor_link import SupervisorLink
from journal.support.time_source import TimeSource


class Clock(Job):
    """The journal's time, and a job that tells the bus Ticked for every live agent every five seconds, in that agent's environment, each listener heard on its own so one that fails stops no other, and one agent's tick that fails stops no other agent's, and one tick at a time, each at the moment it takes its turn, so what a tick decides and records is settled before the next reads it and no tick carries a moment older than one already heard; what the machine says to a tick is typed in through the supervisor; before the tick, an environment whose typing is off while its main agent's stored top state no longer turns it off has it turned on again."""

    interval_seconds = 5.0

    def __init__(self, agents: Agents, bus: Bus, supervisor: SupervisorLink, scope: Scope, time_source: TimeSource, faults: FaultLog, states: StatesCatalogue) -> None:
        self.faults, self.states = faults, states
        self.agents, self.bus, self.supervisor, self.scope, self.time_source = agents, bus, supervisor, scope, time_source
        self.tick_lock = threading.RLock()

    def time(self) -> float:
        return self.time_source.seconds()

    def tick(self, time: float) -> None:
        for agent in self.agents.active_main_agents():
            with self.scope.environment(agent.environment_id):
                self.typing_followed(agent)
        self.bus.dispatch_guarded(ClockTicked(time=time))
        for agent in self.agents.active_main_agents():
            with self.scope.environment(agent.environment_id):
                self.agent_tick(agent)

    def typing_followed(self, agent: Agent) -> None:
        """Typing switched off for the environment comes back on when the main agent's stored top state no longer switches it off; the switch is read before the row, so a state stored after the read has already switched it."""
        try:
            if self.supervisor.is_typing_disabled(agent.environment_id) and not self.states.stack(self.agents.newest_row(agent)).top().disables_typing():
                self.supervisor.enable(agent.environment_id)
                self.supervisor.release(agent.environment_id)
        except Exception as fault:
            self.faults.reported(f"typing of agent {agent.row_id}", fault)

    def agent_tick(self, agent: Agent) -> None:
        try:
            self._tick(agent)
        except Exception as fault:
            self.faults.reported(f"clock tick of agent {agent.row_id}", fault)

    def _tick(self, agent: Agent) -> None:
        with self.tick_lock:
            time = self.time()
            self.ticked(Ticked(silence_seconds=time - agent.update_time.timestamp(), agent=agent).placed(agent, None, time))

    def ticked(self, event: Ticked) -> list[object]:
        with self.tick_lock:
            return self.bus.dispatch_guarded(event)
