import logging
from typing import Any

from bench.agent import Agent
from bench.agent_utils import run_threads
from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario

logger = logging.getLogger(__name__)


class DoNothing(Agent):
    name = "do_nothing"

    def __init__(self, **kwargs):
        pass

    def pre_game(self, scenario: Scenario, team_id: int, last_events: list[Any]):
        pass

    def post_game(self, scenario: Scenario, team_id: int):
        pass

    def run(self, scenario: Scenario, team_id: int, agent_envs: list[PillagerEnv]):
        run_threads([self.run_agent for _ in range(scenario.num_agents_per_team)], args=[[env] for env in agent_envs])

    def run_agent(self, agent_env: PillagerEnv):
        agent_env.step("await bot.waitForTicks(9999999999);")
        logger.info(f"Agent {agent_env.username} finished")
