import logging
import time

from omegaconf import OmegaConf

from agents import agent_classes
from bench.agent import Agent
from bench.agent_utils import run_threads
from bench.config import Config, ScenarioConfig
from bench.mc_server.mc_server import McServer
from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario
from scenarios import scenario_classes
import voyager.utils as U

logger = logging.getLogger(__name__)


class PillagerBench:
    def __init__(self, args: Config):
        self.args = args
        self.mc_server = McServer(args.mc_port)

    def run(self):
        for scenario_i, scenario in enumerate(self.args.scenarios):
            self.run_scenario(scenario_i, scenario)

    def run_scenario(self, scenario_i: int, scenario_args: ScenarioConfig):
        logger.info(f"Running scenario {scenario_args.name}")

        # Load the scenario
        scenario = scenario_classes[scenario_args.name](**scenario_args.kwargs)
        scenario.scenario_i = scenario_i

        # Save the scenario args
        log_path = f"./logs/scenario{scenario.scenario_i}"
        U.f_mkdir(log_path)
        with open(U.f_join(log_path, "scenario.yaml"), "w+") as fp:
            OmegaConf.save(config=scenario_args, f=fp.name)

        # Load the agents
        agents = ([self.load_agent(scenario_args.agent, scenario_args.agent_kwargs if hasattr(scenario_args, "agent_kwargs") else None)]
                  + [self.load_agent(opponent) for opponent in  scenario_args.opponents])

        if len(agents) != scenario.num_teams:
            raise ValueError(f"Number of opponents for this scenario must be {scenario.num_teams - 1}")

        # Run the scenario
        for episode in range(scenario_args.num_episodes):
            # Start a local Minecraft server
            self.mc_server.run(scenario.world_info)

            self.run_episode(episode, scenario, agents)

            # Stop the local Minecraft server
            # time.sleep(10000)
            self.mc_server.stop()

        # Collect data
        # Repeat with soft reset however many times
        # Repeat with hard reset for however many scenarios
        # Log results

    def run_episode(self, episode_i: int, scenario: Scenario, agents: list[Agent]):
        log_path = f"./logs/scenario{scenario.scenario_i}/episode{episode_i}"
        U.f_mkdir(log_path)
        scenario.episode_i = episode_i
        scenario.log_path = log_path

        # Create the agent environments
        logger.info("Creating agent environments...")
        judges = []
        server_port = self.args.server_port
        for judge_i in range(scenario.num_judges):
            env = PillagerEnv(
                scenario,
                episode_i,
                mc_port=self.args.mc_port,
                server_port=server_port,
                username=scenario.judge_names[judge_i],
                log_path=log_path,
            )
            judges.append(env)
            server_port += 1

        agent_envs = []
        for team_i in range(scenario.num_teams):
            team_envs = []
            agent_envs.append(team_envs)
            for agent_i in range(scenario.num_agents_per_team):
                env = PillagerEnv(
                    scenario,
                    episode_i,
                    team_id=team_i,
                    agent_id=agent_i,
                    mc_port=self.args.mc_port,
                    server_port=server_port,
                    username=scenario.agent_names[team_i][agent_i],
                    log_path=log_path,
                )
                team_envs.append(env)
                server_port += 1

        # Reset the agents
        logger.info("Resetting agents...")
        self.reset_agents(agent_envs + [judges])
        # TODO: Stop if some bots failed to start

        # Pre-game
        logger.info("Running pre-pre-game...")
        self.pre_pre_game(scenario, judges)
        logger.info("Running scenario pre-game...")
        scenario.episode_start_time = 0
        scenario.pre_game(judges)
        logger.info("Running agent pre-game...")
        run_threads([agent.pre_game for agent in agents], args=[
            [scenario, i, [e.last_events for e in agent_envs[i]]] for i in range(scenario.num_teams)
        ])

        # Run the game
        logger.info("Running the game...")
        targets = [agent.run for agent in agents]
        args = [[scenario, i, agent_env] for i, agent_env in enumerate(agent_envs)]
        scenario.episode_start_time = time.time()
        run_threads([scenario.run] + targets, args=[[judges]] + args)
        logger.info("Resetting agents...")
        self.reset_agents(agent_envs + [judges])

        # Post-game
        logger.info("Running scenario post-game...")
        scenario.episode_start_time = 0
        scenario.post_game(judges)
        logger.info("Running agent post-game...")
        run_threads([agent.post_game for agent in agents], args=[[scenario, i] for i in range(scenario.num_teams)])

        # Disconnect all agents
        logger.info("Closing agents...")
        self.close_agents(agent_envs + [judges])

        logger.info("Episode complete")

    def pre_pre_game(self, scenario: Scenario, judges: list[PillagerEnv]):
        judges[0].step(
            U.spawn_commands_2(scenario.agent_names, scenario.spawn_locations)
            + U.gamemode_commands(scenario.agent_names, "survival")
            + U.scores_teams_commands(scenario.agent_names, scenario.team_names, scenario.team_colors)
        )

    def load_agent(self, agent_name: str, agent_kwargs: dict = None) -> Agent:
        kwargs = {}
        if 'agents' in self.args and agent_name in self.args.agents and self.args.agents[agent_name] is not None:
            kwargs.update(self.args.agents[agent_name])
        if agent_kwargs is not None:
            kwargs.update(agent_kwargs)
        return agent_classes[agent_name](**kwargs)

    def reset_agents(self, agent_envs: list[list[PillagerEnv]], mode='soft', timeout=2):
        shared_kwargs = {'options': {'mode': mode, 'wait_ticks': self.args.env_wait_ticks}}
        targets = [env.reset for team_envs in agent_envs for env in team_envs]
        run_threads(targets, shared_kwargs=shared_kwargs)
        time.sleep(timeout)

    def close_agents(self, agent_envs: list[list[PillagerEnv]]):
        targets = [env.close for team_envs in agent_envs for env in team_envs]
        run_threads(targets)
