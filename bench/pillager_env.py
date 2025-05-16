import logging
import time
from string import Template
from typing import Dict, Tuple, SupportsFloat, Any, Optional

from gymnasium.core import ObsType

import voyager.utils as U
from bench.scenario import Scenario
from voyager.control_primitives import load_control_primitives_string
from voyager.env import VoyagerEnv

logger = logging.getLogger(__name__)


class PillagerEnv:
    def __init__(
            self,
            scenario: Scenario,
            episode: int,
            team_id: int = None,
            agent_id: int = None,
            mc_port=None,
            username="bot",
            azure_login=None,
            server_host="http://127.0.0.1",
            server_port=3000,
            request_timeout=10,
            polling_timeout=600,
            polling_interval=1,
            log_path="./logs",
    ):
        self.scenario = scenario
        self.episode = episode
        self.team_id = team_id
        self.agent_id = agent_id
        self.username = username
        self.scenario_programs = load_control_primitives_string(scenario.control_primitives)
        self.base_programs = load_control_primitives_string(["scenario"])
        self.log_path = log_path
        self.reward_item_names = None
        self.team_name = None
        self.last_events = None

        if team_id is not None:
            self.reward_item_names = scenario.team_score_metrics[team_id]
            self.team_name = scenario.team_names[team_id]

        # init env
        self.env = VoyagerEnv(
            mc_port=mc_port,
            username=username,
            azure_login=azure_login,
            server_host=server_host,
            server_port=server_port,
            request_timeout=request_timeout,
            polling_timeout=polling_timeout,
            polling_interval=polling_interval,
            log_path=self.log_path,
        )

    def reset(
        self,
        *,
        seed=None,
        options=None,
    ) -> list[tuple[str, dict[str, any]]]:
        self.last_events = self.env.reset(
            seed=seed,
            options=options,
        )
        return self.last_events

    def close(self):
        for retry in range(3):
            try:
                self.env.close()
                break
            except ConnectionError:
                logger.info('bot close failed, retrying...')
                continue

    def step(
        self,
        code: str,
        programs: Optional[str] = None,
    ) -> Tuple[ObsType, SupportsFloat, bool, bool, Dict[str, Any]]:
        # Add timeout if episode_timeout is set and we have started the episode
        if self.scenario.episode_timeout > 0 and self.scenario.episode_start_time > 0:
            timeout = self.scenario.episode_timeout - (time.time() - self.scenario.episode_start_time)
            code = self.get_code_with_timeout(code, timeout)

        # Increment the team score for the reward items in the bot's possession
        if self.reward_item_names is not None and len(self.reward_item_names) != 0:
            code = (f"await scoreRewards(bot, {U.json_dumps(self.reward_item_names)}, {U.json_dumps(self.team_name)});"
                    + code)

        fail_count = 0
        while True:
            try:
                self.last_events = self.env.step(
                    code,
                    programs=self.base_programs + (programs or self.scenario_programs),
                )
                break
            except Exception as e:
                if fail_count > 5:
                    raise e
                logger.error(f"Error in step: {e}")
                fail_count += 1
                self.env.restart_mineflayer()
                time.sleep(1)

        return self.last_events

    def get_code_with_timeout(self, code: str, timeout: float) -> str:
        template = Template("""
async function mainFunction(bot) {
    $code
}
const result = await Promise.race([
    mainFunction(bot),
    new Promise(resolve => setTimeout(() => resolve('Timeout reached'), $timeout))
]);

if (result === 'Timeout reached') {{
    bot.chat('[episode timeout]');
}}""")
        result = template.safe_substitute({
            "code": code,
            "timeout": str(round(timeout * 1000)),
        })
        return result
