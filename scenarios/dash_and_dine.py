import logging
from abc import ABC

import voyager.utils as U
from bench.agent_utils import run_threads
from bench.mc_server.mc_server import ServerProperties
from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario
from pathlib import Path

logger = logging.getLogger(__name__)


class DashAndDine(Scenario, ABC):
    name = "Dash and Dine"

    def __init__(self, episode_timeout: int = 120):
        super().__init__()
        self.episode_timeout = episode_timeout
        self.center_position = {"x": -5, "y": -56, "z": -1}

        team_code_files = ["dash_and_dine_red.js", "dash_and_dine_blue.js"]
        self.team_codes = [self.load_code(file) for file in team_code_files]

    def load_code(self, filename: str):
        try:
            with open(Path(__file__).parent / filename, "r") as fp:
                return fp.read()
        except FileNotFoundError:
            raise f'Scenario code file not found: {filename}'

    @property
    def world_info(self) -> ServerProperties:
        return ServerProperties(
            allow_nether=False,
            difficulty="peaceful",
            generate_structures=False,
            level_name="Dash and Dine",
            level_type="flat",
            motd="Dash and Dine",
            spawn_animals=True,
            spawn_monsters=False,
            spawn_npcs=False
        )

    @property
    def description(self) -> str:
        return (
            "There is a red team and a blue team. "
            "In the red team are Ryn and Raze. "
            "In the blue team are Byte and Blink. "
            "Craft food items and give them to your team's server to earn points. Your team's server is a player. "
            "You can only give three unique types of food items to your server, but within the same food type you can give an unlimited quantity of items. "
            "The red team's server is called 'Red_Server' and is located at -1 -60 -9. "
            "The blue team's server is called 'Blue_Server' and is located at -1 -60 7. "
            "The ground is located at Y = -61. "
            "Food items give points based on the amount of hunger they restore. "
            "There are shared farms that let you farm ingredients to make food. "
            "The random tick rate is set to 200, so crops in farms regrow very quickly. "
            "The scenario ends after an unknown amount of time. "
            "Try to maximize the number of points you earn in the long run. "
            "The team with the most points at the end wins the game. "
            "You are allowed to sabotage the other team.\n\n"
            "Following are all the points of interest and farms:\n"
            "3 Furnaces with 64 coal each: 2 -59 -1\n"
            "Chest with 64 bowls: -3 -59 -1\n"
            "Chest with 16 buckets and a single cow next to it: -7 -60 -7\n"
            "Chest with eggs connected to a simple egg farm with 14 chickens: -7 -60 5 (~2 eggs per minute)\n"
            "2 crafting tables and a chest with 64 gold nuggets and a netherite hoe: -11 -59 -1\n"
            "3 wide sugar cane farm: -11 -60 -8 (~11 sugar cane per minute)\n"
            "3 wide sweet berry farm: -11 -60 6 (~160 berries per minute)\n"
            "2 high cocao bean farm: -15 -60 -8 (~54 cocoa beans per minute)\n"
            "5 wide melon pumpkin farm: -15 -60 -1 (~125 melon/pumpkin blocks per minute)\n"
            "3 wide beetroot farm: -15 -60 6 (~13 beetroots per minute)\n"
            "3 wide carrot farm: -19 -60 -8 (~35 carrots per minute)\n"
            "5 wide wheat farm: -19 -60 -1 (~17 wheat per minute)\n"
            "3 wide potato farm: -19 -60 6 (~35 potatos per minute)\n\n"
            "Following are all the food items that can be crafted, their recipe, and their point values:\n"
            "Baked Potato: Furnace (Potato), 11\n"
            "Beef: Cow drop, 4.8\n"
            "Beetroot: Farmed, 2.2\n"
            "Beetroot Soup: 6 Beetroot + Bowl, 13.2\n"
            "Bread: 3 Wheat, 11\n"
            "Cake: 3 Milk + 2 Sugar + 3 Wheat + Egg, 16.8\n"
            "Carrot: Farmed, 6.6\n"
            "Chicken: Chicken drop, 3.2\n"
            "Cooked Beef: Furnace (Beef), 20.8\n"
            "Cooked Chicken: Furnace (Chicken), 13.2\n"
            "Cookie: 2 Wheat + Cocoa Beans, 2.4\n"
            "Golden Carrot: 8 Gold Nuggets + Carrot, 20.4\n"
            "Melon Slice: Farmed, 3.2\n"
            "Poisonous Potato: Chance from Potato, 3.2\n"
            "Potato: Farmed, 1.6\n"
            "Pumpkin Pie: Pumpkin + Sugar + Egg, 12.8\n"
            "Sugar: Sugar Cane, 0\n"
            "Sugar Cane: Farmed, 0\n"
            "Sweet Berries: Farmed, 2.4"
        )

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
            [(-5, -60, -10), (-5, -60, -8)],
            [(-5, -60, 6), (-5, -60, 8)]
        ]

    @property
    def team_score_metrics(self) -> list[list[str]]:
        return [[], []]

    @property
    def team_centers(self) -> list[tuple[int, int, int]]:
        return [(-1, -60, -9), (-1, -60, 7)]

    @property
    def team_names(self) -> list[str]:
        return ["red_team", "blue_team"]

    @property
    def team_affiliates(self) -> list[list[str]]:
        return [["Ryn", "Raze", "Red_Server"], ["Byte", "Blink", "Blue_Server"]]

    @property
    def team_colors(self) -> list[str]:
        return ["red", "blue"]

    @property
    def num_judges(self) -> int:
        return 2

    @property
    def judge_names(self) -> list[str]:
        return ["Red_Server", "Blue_Server"]

    @property
    def control_primitives(self) -> list[str]:
        return [
            "mineBlock",
            "craftItem",
            "placeItem",
            "multiAgent",
            "farm",
            "smeltItem",
            "killMob",
            "giveToPlayer",
            "useChest",
            "mineflayer",
        ]

    def pre_game(self, envs: list[PillagerEnv]):
        envs[0].step(
            f"bot.chat('/gamemode creative {envs[0].username}');"
            + f"bot.chat('/gamemode creative {envs[1].username}');"
            + f"bot.chat('/gamerule keepInventory true');"
            + f"bot.chat('/gamerule doDaylightCycle false');"
            + f"bot.chat('/gamerule randomTickSpeed 200');"
            + f"bot.chat('/tp {envs[0].username} {self.team_centers[0][0]} {self.team_centers[0][1]} {self.team_centers[0][2]}');"
            + f"bot.chat('/tp {envs[1].username} {self.team_centers[1][0]} {self.team_centers[1][1]} {self.team_centers[1][2]}');"
            + f"bot.chat('/gamerule spawnRadius 0');"
        )

    def post_game(self, envs: list[PillagerEnv]):
        pass

    def run(self, envs: list[PillagerEnv]):
        # Ensure rewards directory exists
        U.f_mkdir(self.log_path, "rewards")

        targets = [envs[i].step for i in range(self.num_judges)]
        args = [[f"await saveRewards(bot, {U.json_dumps(self.team_names[i])}, '{self.log_path}/rewards/"
                 f"{self.team_names[i]}.txt');" + code] for i, code in enumerate(self.team_codes)]
        run_threads(targets, args=args)

    def run_server(self, env: PillagerEnv, team_name: str, code: str):
        save_dir = f"{self.log_path}/rewards/{team_name}.txt"
        env.step(
            f"await saveRewards(bot, {U.json_dumps(team_name)}, '{save_dir}');"
            + code
        )
