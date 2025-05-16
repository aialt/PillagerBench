import copy
import logging
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import voyager.utils as U
from agents.causal_module import CausalModule
from agents.opponent_module import OpponentModule
from agents.tactics_module import TacticsModule
from bench.agent import Agent
from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario
from voyager import Voyager
from voyager.llm import invoke_with_log

logger = logging.getLogger(__name__)


class TactiCrafter(Agent):
    name = "tacticrafter"

    def __init__(self, **kwargs):
        self.voyager_options = kwargs.get('voyager_options', {})
        self.critic_mode = kwargs.get('critic_mode', 'auto')
        self.save_dir = None
        self.chest_memory = {}
        self.agents = []
        self.result = None
        self.events = None
        self.scenario = None

        self.enable_causal = kwargs.get('enable_causal', True)
        self.enable_opponent = kwargs.get('enable_opponent', True)

        team_tactics = kwargs.get('team_tactics', None)
        negotiator_model_name = kwargs.get('negotiator_model_name', 'gpt-4o')
        negotiator_temperature = kwargs.get('negotiator_temperature', 0.3)
        self.tactics = TacticsModule(team_tactics, negotiator_model_name, negotiator_temperature)

        causal_graph = kwargs.get('causal_graph', None)
        causal_model_name = kwargs.get('causal_model_name', 'gpt-4o')
        causal_temperature = kwargs.get('causal_temperature', 0.3)
        self.causal = CausalModule(causal_model_name, causal_temperature, causal_graph)

        opponent_tactics = kwargs.get('opponent_tactics', None)
        opponent_model_name = kwargs.get('opponent_model_name', 'gpt-4o')
        opponent_temperature = kwargs.get('opponent_temperature', 0.3)
        self.opponent = OpponentModule(opponent_tactics, opponent_model_name, opponent_temperature)

        if 'checkpoint_path' in kwargs:
            checkpoint_path = Path(kwargs['checkpoint_path']).absolute()
            self.load(checkpoint_path)
            logger.info(f"Loaded TactiCrafter checkpoint from {checkpoint_path}")

    def load(self, checkpoint_path: Path):
        # Load the TactiCrafter state from the checkpoint directory
        self.result = U.load_json(checkpoint_path / "code.json")
        self.tactics.team_tactics = U.load_json(checkpoint_path / "tactics.json")
        self.opponent.opponent_tactics = U.load_json(checkpoint_path / "opp_tactics.json")
        self.causal.from_causal_graph(U.load_json(checkpoint_path / "causal_graph.json"))

    def pre_game(self, scenario: Scenario, team_id: int, last_events: list[Any]):
        self.save_dir = f"{scenario.log_path}/{scenario.team_names[team_id]}"
        U.f_mkdir(self.save_dir)
        self.chest_memory = {}
        self.agents = []
        self.scenario = scenario

        # Get events from previous episode
        events = self.fix_chat_events(self.result, scenario, team_id)[scenario.agent_names[team_id][0]]['events'] if self.result else None
        opponent_id = 1 - team_id

        # update tactics
        if self.enable_causal:
            self.causal.step(scenario, team_id, self.result, self.save_dir)

        if self.enable_opponent:
            self.opponent.step(
                scenario, opponent_id, events, self.save_dir,
                causal_graph=self.causal.get_causal_graph()
            )

        self.tactics.step(
            scenario, team_id, events, self.save_dir,
            chest_memory=self.chest_memory,
            causal_graph=self.causal.get_causal_graph(),
            opp_tactics=self.opponent.opponent_tactics if self.enable_opponent else None
        )

        # create Voyager agents
        for i in range(scenario.num_agents_per_team):
            username = scenario.agent_names[team_id][i]
            ckpt_dir = f"{self.save_dir}/{username}_ckpt"

            agent = Voyager(
                username=username,
                ckpt_dir=ckpt_dir,
                control_primitives=scenario.control_primitives,
                **self.voyager_options
            )
            self.agents.append(agent)

        # reset agents or load previous state
        if self.result:
            for i, agent in enumerate(self.agents):
                agent.task = scenario.team_objectives[team_id]
                agent.tactics = self.tactics.team_tactics
                agent.scenario = scenario.description
                agent.context = ""
                agent.events = last_events[i]
                self.update_agent(
                    agent,
                    self.result[agent.username]['parsed_result'],
                    last_events[i],
                    self.result[agent.username]['success'],
                    self.result[agent.username]['critique'],
                )
        else:
            self.run_threads(lambda a, _, args: a.reset(**args), args={agent.username: {'args':
                {
                    'task': scenario.team_objectives[team_id],
                    'tactics': self.tactics.team_tactics,
                    'scenario': scenario.description,
                    'context': "",
                    'events': last_events[i],
                    'reset_env': False,
                }
            } for i, agent in enumerate(self.agents)})

        # get ai_message and parse in parallel
        logger.info('get_ai_message_parse')
        self.result = self.run_threads(self.get_ai_message_parse)

    def run(self, scenario: Scenario, team_id: int, agent_envs: list[PillagerEnv]):
        # Assign environments to agents
        for agent, env in zip(self.agents, agent_envs):
            agent.env = env

        # do run_agent in parallel
        logger.info('env_step')
        self.run_threads(self.run_agent)

    def run_agent(self, agent, _):
        for _ in range(agent.action_agent_task_max_retries):
            parsed_result = self.result[agent.username]['parsed_result']
            events = self.env_step(agent, parsed_result)

            # Accumulate events for all retries
            if 'events' in self.result[agent.username]:
                self.result[agent.username]['events'].extend(events)
            else:
                self.result[agent.username].update({'events': events})

            # Dedupe events for critic and update agent
            events = self.dedupe_events(events)

            # Critic response
            success, critique = self.check_task_success(agent, events)
            self.result[agent.username].update({'success': success, 'critique': critique})

            # update agents (note this function does not need to be run with threads; could add a flag to just iterate)
            messages, done, info = self.update_agent(agent, parsed_result, events, success, critique)
            self.result[agent.username].update({'info': info})

            # Stop if either agent max retries reached or timeout
            if done or (0 < self.scenario.episode_timeout < time.time() - self.scenario.episode_start_time
                        and 0 < self.scenario.episode_start_time):
                break

            # Get AI message and parse
            self.get_ai_message_parse(agent, self.result[agent.username])

    def post_game(self, scenario: Scenario, team_id: int):
        # Remove duplicate events
        self.dedupe_results(self.result)

        # Save previous events, code, tactics, critique
        self.save_episode(self.result)

    def dedupe_events(self, events):
        """
        When consecutive onChat events form a repeating block (by comparing the value of the "onChat" key),
        collapse the repeated copies to a single copy.
        """
        # Save the index for each event
        i_events = [(i, event) for i, event in enumerate(events)]

        # Group the chat events by username
        chat_events = defaultdict(list)
        non_chat_events = []
        for i, (event_type, event_data) in i_events:
            if event_type == "onChat":
                split_index = event_data["onChat"].find('>')
                chatter = event_data["onChat"][1:split_index]
                chat_events[chatter].append((i, (event_type, event_data)))
            else:
                non_chat_events.append((i, (event_type, event_data)))

        # Dedupe all chatters individually
        for chatter, c_events in chat_events.items():
            if all(chatter not in team_names for team_names in self.scenario.agent_names):
                continue

            new_events = []
            i = 0
            while i < len(c_events):
                _, (event_type, event_data) = c_events[i]
                # Process only onChat events with our duplicate-compression algorithm.
                if event_type != "onChat":
                    new_events.append(c_events[i])
                    i += 1
                    continue

                # For an onChat event, try to detect a repeating block.
                # We'll try possible block lengths (L) starting at the current index.
                max_possible_L = (len(c_events) - i) // 2  # At least two copies required
                chosen_L = None
                for L in range(1, max_possible_L + 1):
                    # Build the block for comparison: the sequence of onChat values.
                    block = [c_events[j][1][1].get("onChat") for j in range(i, i + L)]
                    # Compare to the immediately following block of the same length.
                    next_block = [c_events[j][1][1].get("onChat") for j in range(i + L, i + 2 * L)]
                    if block == next_block:
                        chosen_L = L
                        break  # Choose the smallest L that repeats

                if chosen_L is not None:
                    # We found a repeating block. Now count how many consecutive copies there are.
                    block_values = [c_events[j][1][1].get("onChat") for j in range(i, i + chosen_L)]
                    j = i
                    count = 0
                    while j + chosen_L <= len(c_events):
                        current_block = [c_events[k][1][1].get("onChat") for k in range(j, j + chosen_L)]
                        if current_block == block_values:
                            count += 1
                            j += chosen_L
                        else:
                            break
                    # Append the block once (discarding the duplicate copies)
                    new_events.extend(c_events[i:i + chosen_L])
                    i += count * chosen_L
                else:
                    # No repeating block found at this position; just copy the single event.
                    new_events.append(c_events[i])
                    i += 1

            chat_events[chatter] = new_events

        # Reconstruct the list of events from the grouped chat events and the non-chat events.
        new_events = non_chat_events
        for chatter, c_events in chat_events.items():
            new_events.extend(c_events)
        new_events.sort(key=lambda x: x[0])

        # Remove the indices
        new_events = [event for _, event in new_events]

        return new_events

    def dedupe_results(self, data) -> None:
        for outer_key, inner in data.items():
            events = inner.get("events", [])
            logger.info(f"Initial length of events for {outer_key}: {len(events)}")
            inner["events"] = self.dedupe_events(events)
            logger.info(f"Final length of events for {outer_key}: {len(inner['events'])}")

    # Prepare code for run step
    # get ai_message and parse
    def get_ai_message_parse(self, agent, result):
        if agent.action_agent_rollout_num_iter < 0:
            raise ValueError("Agent must be reset before stepping")
        ai_message = invoke_with_log(agent.action_agent.llm, agent.messages, prefix="Action ")
        agent.logger(f"\033[34m****Action Agent ai message****\n{ai_message.content}\033[0m")
        agent.conversations.append(
            (agent.messages[0].content, agent.messages[1].content, ai_message.content)
        )
        parsed_result = agent.action_agent.process_ai_message(message=ai_message)
        result.update({'parsed_result': parsed_result})

    def env_step(self, agent, parsed_result):
        if not isinstance(parsed_result, dict):
            assert isinstance(parsed_result, str)
            print('parsed_result', parsed_result)
            agent.recorder.record([], agent.task)
            agent.logger(f"\033[34m{parsed_result} Trying again!\033[0m")
            return []

        code = parsed_result["program_code"] + "\n" + parsed_result["exec_code"]
        events = agent.env.step(code, programs=agent.skill_manager.programs)
        agent.recorder.record(events, agent.task)  # what is this for??
        self.update_chest_memory(events[-1][1]["nearbyChests"])
        return events

    # update messages for next round
    def update_agent(self, agent, parsed_result, events, success, critique):
        new_skills = agent.skill_manager.retrieve_skills(
            query=agent.context
                  + "\n\n"
                  + agent.action_agent.summarize_chatlog(events)
        )
        system_message = agent.action_agent.render_system_message(skills=new_skills)
        human_message = agent.action_agent.render_human_message(
            events=events,
            code=parsed_result["program_code"] if isinstance(parsed_result, dict) else None,
            task=agent.task,
            tactics=self.tactics.team_tactics,
            prev_tactics=self.tactics.prev_team_tactics,
            scenario=agent.scenario,
            context=agent.context,
            critique=critique,
        )
        agent.last_events = copy.deepcopy(events)
        agent.messages = [system_message, human_message]
        assert len(agent.messages) == 2
        agent.action_agent_rollout_num_iter += 1

        done = (
                agent.action_agent_rollout_num_iter >= agent.action_agent_task_max_retries
        )
        info = {
            "task": agent.task,
            "success": success,
            "conversations": agent.conversations,
            "rollout_num_iter": agent.action_agent_rollout_num_iter,
        }
        if success:
            assert (
                    "program_code" in parsed_result and "program_name" in parsed_result
            ), "program and program_name must be returned when success"
            info["program_code"] = parsed_result["program_code"]
            info["program_name"] = parsed_result["program_name"]

        agent.logger(
            f"\033[32m****Action Agent human message****\n{agent.messages[-1].content}\033[0m"
        )

        return agent.messages, done, info

    def check_task_success(self, agent, events, max_retries=5):

        def ai_check_task_success(agent, events):
            critic_agent = agent.critic_agent

            human_message = critic_agent.render_human_message(
                events=events,
                task=agent.task,
                scenario=self.scenario.description,
                tactics=self.tactics.team_tactics,
                context=agent.context,
                chest_observation=agent.action_agent.render_chest_observation(),
            )
            messages = [
                critic_agent.render_system_message(),
                human_message,
            ]
            critic_response = critic_agent.ai_check_task_success(
                messages=messages, max_retries=max_retries
            )

            success, critique = critic_response

            return success, critique

        def human_check_task_success(agent):
            # log critic human critic messages
            agent.critic_agent.render_human_message(
                events=events,
                task=agent.task,
                scenario=self.scenario.description,
                tactics=self.tactics.team_tactics,
                context=agent.context,
                chest_observation=agent.action_agent.render_chest_observation(),
            )

            # collect critiques about agent
            confirmed = False
            success = False
            critique = ""
            while not confirmed:
                success = input(f"{agent.username} Success? (y/n)")
                success = success.lower() == "y"
                critique = input("Enter your critique:")
                print(f"Success: {success}\nCritique: {critique}")
                confirmed = input("Confirm? (y/n)") in ["y", ""]

            return success, critique

        if len(events) == 0:
            return False, None

        if self.critic_mode == "manual":
            return human_check_task_success(agent)

        return ai_check_task_success(agent, events)

    # replace chat events with those from the agent who lived longest and save both players observations
    # note: this is a hacky solution to a problem that should be fixed in the future
    def fix_chat_events(self, events, scenario, team_id):
        # collect all chat events for each agent
        agents = scenario.agent_names[team_id]
        chat_events = {username: [] for username in agents}
        other_events = {username: [] for username in agents}
        for username in agents:
            other_agents = [a for a in agents if a != username]
            if 'events' not in events[username]:
                continue
            for (event_type, event) in events[username]['events']:
                if event_type == 'onChat':
                    chat_events[username].append((event_type, event))
                # record both agents observations for reading inventory etc
                elif event_type == 'observe':
                    for other_username in other_agents:
                        other_events[other_username].insert(0, ('otherObserve', event))
                    other_events[username].append((event_type, event))
                else:
                    other_events[username].append((event_type, event))
        # copy in longest thread of chats
        longest_thread = max(chat_events.values(), key=len)
        new_events = {username: {'events': longest_thread + other_events[username]} for username in agents}

        return new_events

    def save_episode(self, results):
        U.dump_json(results, f"{self.save_dir}/code.json")

    def run_threads(self, target, args=None, shared_args=False):
        """
        Runs target function in parallel for each agent. args is a dictionary of arguments to pass to each thread, where the key is the agent's username.

        For example,
        args = {'Voyager3000': {'arg1': 1, 'arg2': 2}, 'Voyager3001': {'arg1': 3, 'arg2': 4}}
        """
        if args is None:
            args = {agent.username: {} for agent in self.agents}
        if shared_args:
            args = {agent.username: args for agent in self.agents}

        results = {}
        threads = []
        for agent in self.agents:
            result = {}
            thread = threading.Thread(target=target, args=(agent, result), kwargs=args[agent.username], daemon=True)
            results[agent.username] = result
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        return results

    # update a global chest memory to keep consistent across agents
    def update_chest_memory(self, chests):
        for position, chest in chests.items():
            if position in self.chest_memory:
                if isinstance(chest, dict):
                    self.chest_memory[position] = chest
                if chest == "Invalid":
                    print(
                        f"\033[32mRemoving chest {position}: {chest}\033[0m"
                    )
                    self.chest_memory.pop(position)
            else:
                if chest != "Invalid":
                    print(f"\033[32mSaving chest {position}: {chest}\033[0m")
                    self.chest_memory[position] = chest

        # update agent chest memories
        for agent in self.agents:
            agent.action_agent.chest_memory = self.chest_memory
