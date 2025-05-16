import logging
import time
from abc import ABC

import voyager.utils as U
from bench.mc_server.mc_server import ServerProperties
from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario
from pathlib import Path

logger = logging.getLogger(__name__)


class MushroomWar(Scenario, ABC):
    name = "Mushroom War"

    def __init__(self, episode_timeout: int = 120):
        super().__init__()
        self.episode_timeout = episode_timeout
        self.center_position = {"x": -9, "y": -56, "z": -2}

        try:
            with open(Path(__file__).parent / "mushroom_war.js", "r") as fp:
                self.scenario_code = fp.read()
        except FileNotFoundError:
            raise 'No scenario code file found'

        self.block_positions = self._get_block_positions()
        self.block_types = list(self.block_positions.keys())

    @property
    def world_info(self) -> ServerProperties:
        return ServerProperties(
            allow_nether=False,
            difficulty="peaceful",
            generate_structures=False,
            level_name="Mushroom War",
            level_type="flat",
            motd="Mushroom War",
            spawn_animals=False,
            spawn_monsters=False,
            spawn_npcs=False
        )

    def _get_block_positions(self) -> dict[str, list[dict[str, int]]]:
        return {
            "slime_block": [{"x": -9, "y": -60, "z": -7}, {"x": -9, "y": -60, "z": 3}, {"x": -9, "y": -60, "z": -8}, {"x": -9, "y": -60, "z": 4}, {"x": -10, "y": -60, "z": -8}, {"x": -8, "y": -60, "z": -8}, {"x": -10, "y": -60, "z": 4}, {"x": -8, "y": -60, "z": 4}, {"x": -9, "y": -60, "z": -9}, {"x": -9, "y": -60, "z": 5}, {"x": -13, "y": -60, "z": -11}, {"x": -5, "y": -60, "z": -11}, {"x": -13, "y": -60, "z": 7}, {"x": -5, "y": -60, "z": 7}, {"x": -12, "y": -60, "z": -12}, {"x": -6, "y": -60, "z": -12}, {"x": -12, "y": -60, "z": 8}, {"x": -6, "y": -60, "z": 8}, {"x": -13, "y": -60, "z": -12}, {"x": -5, "y": -60, "z": -12}, {"x": -13, "y": -60, "z": 8}, {"x": -5, "y": -60, "z": 8}, {"x": -14, "y": -60, "z": -12}, {"x": -4, "y": -60, "z": -12}, {"x": -14, "y": -60, "z": 8}, {"x": -4, "y": -60, "z": 8}, {"x": -13, "y": -60, "z": -13}, {"x": -5, "y": -60, "z": -13}, {"x": -13, "y": -60, "z": 9}, {"x": -5, "y": -60, "z": 9}],
            "red_mushroom_block": [{"x": -13, "y": -59, "z": -7}, {"x": -5, "y": -59, "z": -7}, {"x": -12, "y": -59, "z": -8}, {"x": -6, "y": -59, "z": -8}, {"x": -13, "y": -58, "z": -8}, {"x": -5, "y": -58, "z": -8}, {"x": -14, "y": -59, "z": -8}, {"x": -4, "y": -59, "z": -8}, {"x": -13, "y": -59, "z": -9}, {"x": -5, "y": -59, "z": -9}, {"x": -9, "y": -59, "z": -11}, {"x": -10, "y": -59, "z": -12}, {"x": -8, "y": -59, "z": -12}, {"x": -9, "y": -58, "z": -12}, {"x": -9, "y": -59, "z": -13}],
            "brown_mushroom_block": [{"x": -13, "y": -59, "z": 3}, {"x": -5, "y": -59, "z": 3}, {"x": -12, "y": -59, "z": 4}, {"x": -6, "y": -59, "z": 4}, {"x": -13, "y": -58, "z": 4}, {"x": -5, "y": -58, "z": 4}, {"x": -14, "y": -59, "z": 4}, {"x": -4, "y": -59, "z": 4}, {"x": -13, "y": -59, "z": 5}, {"x": -5, "y": -59, "z": 5}, {"x": -9, "y": -59, "z": 7}, {"x": -10, "y": -59, "z": 8}, {"x": -8, "y": -59, "z": 8}, {"x": -9, "y": -58, "z": 8}, {"x": -9, "y": -59, "z": 9}],
            "mushroom_stem": [{"x": -13, "y": -60, "z": -8}, {"x": -5, "y": -60, "z": -8}, {"x": -13, "y": -60, "z": 4}, {"x": -5, "y": -60, "z": 4}, {"x": -13, "y": -59, "z": -8}, {"x": -5, "y": -59, "z": -8}, {"x": -13, "y": -59, "z": 4}, {"x": -5, "y": -59, "z": 4}, {"x": -9, "y": -60, "z": -12}, {"x": -9, "y": -60, "z": 8}, {"x": -9, "y": -59, "z": -12}, {"x": -9, "y": -59, "z": 8}]
        }

    @property
    def description(self) -> str:
        return ("There is a red team and a blue team. "
                "In the red team are Ryn and Raze. "
                "In the blue team are Byte and Blink. "
                "The red team is located at -9 -60 -10. "
                "The blue team is located at -9 -60 6. "
                "The ground is located at Y = -61. "
                "Both teams have a designated area which is a sphere with a 7 block radius from the center. "
                "Both team areas have been polluted with slime blocks. "
                "In the red team area there are three giant mushrooms each containing 5 red mushroom blocks. "
                "In the blue team area there are three giant mushrooms each containing 5 brown mushroom blocks. "
                "Harvesting a mushroom block yields 0-2 (usually 0) mushrooms. "
                "However, mushroom blocks only regrow if the number of slime blocks in the team area is 7 or below. "
                "The slime blocks will be quickly repolluted after slime is removed. "
                "The scenario ends after an unknown amount of time. "
                "The red team gets rewarded 1 point for each red mushroom they collect. "
                "The blue team gets rewarded 1 point for each brown mushroom they collect. "
                "The team with the most points at the end wins the game. "
                "There are no chests. "
                "You are allowed to sabotage the other team.")

    @property
    def num_teams(self) -> int:
        return 2

    @property
    def num_agents_per_team(self) -> int:
        return 2

    @property
    def agent_names(self) -> list[list[str]]:
        return [["Ryn", "Raze"], ["Byte", "Blink"]]

    @property
    def team_objectives(self) -> list[str]:
        return [
            "You are in the red team. Win the game.",
            "You are in the blue team. Win the game."
        ]

    @property
    def spawn_locations(self) -> list[list[tuple[int, int, int]]]:
        return [
            [(-7, -60, -10), (-11, -60, -10)],
            [(-11, -60, 6), (-7, -60, 6)]
        ]

    @property
    def team_score_metrics(self) -> list[list[str]]:
        return [
            ["red_mushroom"],
            ["brown_mushroom"]
        ]

    @property
    def team_collectable_block_names(self) -> list[str]:
        return ["red_mushroom_block", "brown_mushroom_block"]

    @property
    def team_centers(self) -> list[tuple[int, int, int]]:
        return [(-9, -60, -10), (-9, -60, 6)]

    @property
    def team_names(self) -> list[str]:
        return ["red_team", "blue_team"]

    @property
    def team_colors(self) -> list[str]:
        return ["red", "blue"]

    @property
    def control_primitives(self) -> list[str]:
        return [
            "mineBlock",
            "placeItem",
            "multiAgent",
            "killMob",
            "giveToPlayer",
            "mineflayer",
        ]

    def pre_game(self, envs: list[PillagerEnv]):
        env = envs[0]
        env.step(
            f"bot.chat('/gamemode spectator {env.username}');"
            + f"bot.chat('/gamerule keepInventory true');"
            + f"bot.chat('/gamerule doDaylightCycle false');"
            + f"bot.chat('/tp {env.username} {self.center_position['x']} {self.center_position['y']} {self.center_position['z']}');"  # move this into a helper?
            + f"bot.chat('/gamerule randomTickSpeed 3');"
            + f"bot.chat('/gamerule spawnRadius 0');"
            # + U.remove_drops_commands()
            # + U.remove_blocks_commands(self.block_types, self.center_position)
            # + U.add_block_commands(self.block_positions)
        )

    def post_game(self, envs: list[PillagerEnv]):
        pass

    def run(self, envs: list[PillagerEnv]):
        # Ensure rewards directory exists
        U.f_mkdir(self.log_path, "rewards")

        envs[0].step(
            f"await saveRewards(bot, {U.json_dumps(self.team_names[0])}, '{self.log_path}/rewards/{(self.team_names[0])}.txt');"
            + f"await saveRewards(bot, {U.json_dumps(self.team_names[1])}, '{self.log_path}/rewards/{(self.team_names[1])}.txt');"
            + self.scenario_code
        )
