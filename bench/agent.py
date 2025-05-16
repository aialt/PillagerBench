import abc
from typing import Any

from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario


class Agent(abc.ABC):
    @abc.abstractmethod
    def pre_game(self, scenario: Scenario, team_id: int, last_events: list[Any]):
        pass
    
    @abc.abstractmethod
    def post_game(self, scenario: Scenario, team_id: int):
        pass

    @abc.abstractmethod
    def run(self, scenario: Scenario, team_id: int, agent_envs: list[PillagerEnv]):
        pass
