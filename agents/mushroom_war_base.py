import logging
import time
from pathlib import Path
from typing import Any

from bench.agent import Agent
from bench.agent_utils import load_script, run_threads
from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario
from scenarios.mushroom_war import MushroomWar

logger = logging.getLogger(__name__)


class MushroomWarBase(Agent):
    name = "mushroom_war_base"

    def __init__(self, **kwargs):
        self.agent_scripts = []
        self.scenario = None

    def pre_game(self, scenario: MushroomWar, team_id: int, last_events: list[Any]):
        self.scenario = scenario
        opponent_id = 1 - team_id
        info = {
            "team_name": scenario.team_names[team_id],
            "team_center": scenario.team_centers[team_id],
            "team_collectable_block_name": scenario.team_collectable_block_names[team_id],
            "opponent_name": scenario.team_names[opponent_id],
            "opponent_center": scenario.team_centers[opponent_id],
            "opponent_collectable_block_name": scenario.team_collectable_block_names[opponent_id]
        }

        # Load the agent scripts with info inserted
        self.agent_scripts = []
        for i in range(scenario.num_agents_per_team):
            script_path = Path(__file__).parent / "scripts" / f"{self.name}_{i}.js"
            script = load_script(script_path, info)
            self.agent_scripts.append(script)

    def post_game(self, scenario: Scenario, team_id: int):
        pass

    def run(self, scenario: Scenario, team_id: int, agent_envs: list[PillagerEnv]):
        run_threads([self.run_agent for _ in range(scenario.num_agents_per_team)], args=list(zip(agent_envs, self.agent_scripts)))

    def run_agent(self, agent_env: PillagerEnv, agent_script: str):
        for _ in range(10):
            agent_env.step(agent_script)
            # Stop if timeout
            if (0 < self.scenario.episode_timeout < time.time() - self.scenario.episode_start_time
                        and 0 < self.scenario.episode_start_time):
                break

        logger.info(f"Agent {agent_env.username} finished")

