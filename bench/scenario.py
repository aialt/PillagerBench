import abc

from bench.mc_server.mc_server import ServerProperties
from voyager.control_primitives import load_control_primitives_string


class Scenario(abc.ABC):
    def __init__(self):
        self.scenario_i = 0
        self.episode_i = 0
        self.log_path = "./logs"
        self.episode_start_time = 0
        self.episode_timeout = 0

    @property
    @abc.abstractmethod
    def name(self) -> str:
        return ""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        return ""

    @property
    @abc.abstractmethod
    def num_teams(self) -> int:
        return 1

    @property
    @abc.abstractmethod
    def num_agents_per_team(self) -> int:
        return 1
    
    @property
    @abc.abstractmethod
    def team_objectives(self) -> list[str]:
        return []

    @property
    @abc.abstractmethod
    def team_score_metrics(self) -> list[list[str]]:
        return [[]]

    @property
    @abc.abstractmethod
    def team_names(self) -> list[str]:
        return ["red_team"]

    @property
    def team_affiliates(self) -> list[list[str]]:
        return self.agent_names

    @property
    @abc.abstractmethod
    def team_colors(self) -> list[str]:
        return ["red"]

    @property
    def num_judges(self) -> int:
        return 1

    @property
    def judge_names(self) -> list[str]:
        return ["Judy"]

    @property
    @abc.abstractmethod
    def control_primitives(self) -> list[str]:
        return [
            "exploreUntil",
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

    @property
    def programs(self) -> str:
        return load_control_primitives_string()

    @property
    @abc.abstractmethod
    def world_info(self) -> ServerProperties:
        return ServerProperties()

    @property
    @abc.abstractmethod
    def agent_names(self) -> list[list[str]]:
        pass

    @property
    @abc.abstractmethod
    def spawn_locations(self) -> list[list[tuple[int, int, int]]]:
        pass

    @abc.abstractmethod
    def pre_game(self, envs):
        pass

    @abc.abstractmethod
    def post_game(self, envs):
        pass

    @abc.abstractmethod
    def run(self, envs):
        pass



