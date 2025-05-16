import logging
import re
import time
from collections import defaultdict
from typing import Any

from javascript import require
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import SystemMessagePromptTemplate

import voyager.utils as U
from bench.agent import Agent
from bench.agent_utils import run_threads
from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario
from voyager.control_primitives_context import load_control_primitives_context
from voyager.llm import create_llm, invoke_with_log
from voyager.prompts import load_prompt

logger = logging.getLogger(__name__)


class CotAgent(Agent):
    name = "cot_agent"

    def __init__(self, **kwargs):
        self.save_dir = None
        self.result = None
        self.scenario: Scenario | None = None
        self.llm = create_llm("gpt-4o-2024-08-06", 0.3, 120)
        self.control_primitives_context = []
        self.team_id = 0

    def pre_game(self, scenario: Scenario, team_id: int, last_events: list[Any]):
        self.save_dir = f"{scenario.log_path}/{scenario.team_names[team_id]}"
        U.f_mkdir(self.save_dir)
        self.scenario = scenario
        self.team_id = team_id
        self.control_primitives_context = load_control_primitives_context(scenario.control_primitives)

        # Get voxels and entities from the last event
        voxels = None
        entities = None
        assert len(last_events[0]) == 0 or last_events[0][-1][0] == "observe", "Last event must be observe"
        for i, (event_type, event) in enumerate(last_events[0]):
            if event_type == "observe":
                voxels = event["voxels"]
                entities = event["status"]["entities"]
                assert i == len(last_events[0]) - 1, "observe must be the last event"

        # Get events from previous episode
        events = self.fix_chat_events(self.result, scenario, team_id)[scenario.agent_names[team_id][0]]['events'] if self.result else []

        # Generate system message
        system_message = self.render_system_message()

        # Generate human message
        human_message = self.render_human_message(events=events, voxels=voxels, entities=entities)

        # Generate AI message
        ai_message = invoke_with_log(self.llm, [system_message, human_message], prefix="CoT ")
        logger.info(f"\033[34m****CoT Agent ai message****\n{ai_message.content}\033[0m")

        # Process AI message
        agent_scripts = self.process_ai_message(ai_message)
        self.result = {scenario.agent_names[team_id][i]: {"program": agent_scripts[i]} for i in range(scenario.num_agents_per_team)}

    def post_game(self, scenario: Scenario, team_id: int):
        # Remove duplicate events
        self.dedupe_results(self.result)

        # Save episode
        self.save_episode(self.result)

    def run(self, scenario: Scenario, team_id: int, agent_envs: list[PillagerEnv]):
        run_threads([self.run_agent for _ in range(scenario.num_agents_per_team)], args=list(zip(agent_envs)))

    def run_agent(self, agent_env: PillagerEnv):
        username = agent_env.username

        for _ in range(10):
            agent_script = self.result[username]["program"]["program_code"] + '\n' + self.result[username]["program"]["exec_code"]
            events = agent_env.step(agent_script)

            # Accumulate events for all retries
            if 'events' in self.result[username]:
                self.result[username]['events'].extend(events)
            else:
                self.result[username].update({'events': events})

            # Stop if timeout
            if (0 < self.scenario.episode_timeout < time.time() - self.scenario.episode_start_time
                        and 0 < self.scenario.episode_start_time):
                break

        logger.info(f"Agent {username} finished")

    def render_system_message(self):
        system_template = load_prompt("cot_prompt")
        programs = "\n\n".join(self.control_primitives_context)
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
        response_format = load_prompt("action_response_format2")
        system_message = system_message_prompt.format(programs=programs, response_format=response_format)
        assert isinstance(system_message, SystemMessage)
        return system_message

    def render_human_message(
        self, *, events, voxels=None, entities=None
    ):
        chat_messages = []
        error_messages = []

        assert len(events) == 0 or events[-1][0] == "observe", "Last event must be observe"
        for i, (event_type, event) in enumerate(events):
            if event_type == "onChat":
                chat_messages.append(event["onChat"])
            elif event_type == "onError":
                error_messages.append(event["onError"])

        observation = ""

        if self.result:
            observation += f"Code from the last round:\n"
            for i in range(self.scenario.num_agents_per_team):
                observation += f"Code agent {i + 1}:\n```javascript\n{self.result[self.scenario.agent_names[self.team_id][i]]['program']['program_code']}\n```\n\n"
        else:
            observation += f"Code from the last round: No code in the first round\n\n"

        if error_messages:
            error = "\n".join(error_messages)
            observation += f"Execution error:\n{error}\n\n"
        else:
            observation += f"Execution error: No error\n\n"

        if chat_messages:
            chat_log = "\n".join(chat_messages)
            observation += f"Chat log: {chat_log}\n\n"
        else:
            observation += f"Chat log: None\n\n"

        if voxels:
            observation += f"Nearby blocks: {', '.join(voxels)}\n\n"
        else:
            observation += f"Nearby blocks: None\n\n"

        if entities:
            nearby_entities = [
                k for k, v in sorted(entities.items(), key=lambda x: x[1])
            ]
            observation += f"Nearby entities (nearest to farthest): {', '.join(nearby_entities)}\n\n"
        else:
            observation += f"Nearby entities (nearest to farthest): None\n\n"

        observation += f"Team name: You are {self.scenario.team_names[self.team_id]}\n\n"

        observation += f"Team agents: {', '.join(self.scenario.agent_names[self.team_id])}\n\n"

        observation += f"Scenario: {self.scenario.description}\n\n"

        observation += f"Task: {self.scenario.team_objectives[self.team_id]}\n\n"

        return HumanMessage(content=observation)

    def process_ai_message(self, message):
        assert isinstance(message, AIMessage)

        retry = 3
        error = None
        while retry > 0:
            try:
                babel = require("@babel/core")
                babel_generator = require("@babel/generator").default

                code_pattern = re.compile(r"```(?:javascript|js)(.*?)```", re.DOTALL)
                codes = code_pattern.findall(message.content)
                result = []
                for code in codes:
                    parsed = babel.parse(code)
                    functions = []
                    assert len(list(parsed.program.body)) > 0, "No functions found"
                    for i, node in enumerate(parsed.program.body):
                        if node.type != "FunctionDeclaration":
                            continue
                        node_type = (
                            "AsyncFunctionDeclaration"
                            if node["async"]
                            else "FunctionDeclaration"
                        )
                        functions.append(
                            {
                                "name": node.id.name,
                                "type": node_type,
                                "body": babel_generator(node).code,
                                "params": list(node["params"]),
                            }
                        )
                    # find the last async function
                    main_function = None
                    for function in reversed(functions):
                        if function["type"] == "AsyncFunctionDeclaration":
                            main_function = function
                            break
                    assert (
                        main_function is not None
                    ), "No async function found. Your main function must be async."
                    assert (
                        len(main_function["params"]) == 1
                        and main_function["params"][0].name == "bot"
                    ), f"Main function {main_function['name']} must take a single argument named 'bot'"
                    program_code = "\n\n".join(function["body"] for function in functions)
                    exec_code = f"await {main_function['name']}(bot);"
                    result.append(
                        {
                            "program_code": program_code,
                            "program_name": main_function["name"],
                            "exec_code": exec_code,
                        }
                    )
                return result
            except Exception as e:
                retry -= 1
                error = e
                time.sleep(1)
        return f"Error parsing action response (before program execution): {error}"

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
