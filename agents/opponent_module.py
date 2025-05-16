import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from bench.scenario import Scenario
from voyager.llm import create_llm, invoke_with_log
from voyager.prompts import load_prompt

logger = logging.getLogger(__name__)

class OpponentModule:
    def __init__(
            self,
            team_tactics=None,
            opponent_model_name="gpt-4o",
            opponent_temperature=0.7,
    ):
        self.opponent_tactics = team_tactics or "unknown"
        self.opponent_model_name = opponent_model_name
        self.opponent_temperature = opponent_temperature

        self.llm = create_llm(
            model_name=opponent_model_name,
            temperature=opponent_temperature,
            request_timeout=120,
        )

    def step(self, scenario, team_id, events, save_dir, causal_graph):
        if events is not None:
            logger.info("Updating opponent tactics based on events.")
            self.update_tactics(scenario, team_id, events, causal_graph)

        # save tactics to file
        with open(f"{save_dir}/opp_tactics.json", 'w') as tactics_file:
            # noinspection PyTypeChecker
            json.dump(self.opponent_tactics, tactics_file, indent=4)

    def update_tactics(self, scenario: Scenario, opponent_id: int, events, causal_graph):
        """
        Updates the tactics based on the events that have occurred.
        """
        messages = [
            self.render_system_message(scenario, opponent_id, causal_graph),
            self.render_human_message(events, scenario, opponent_id),
        ]

        for _ in range(3):
            response = invoke_with_log(self.llm, messages, prefix="Opponent ")
            content = response.content

            if '<think>' in content and '</think>' in content:
                # Strip any thinking content from the response for reasoning models
                split_content = content.split('<think>')
                message = split_content[1].split('</think>')[1].strip()
            else:
                # Parsing the response based on the new structure
                message = content.strip()

            logger.info(f"\033[94mOpponent AI message: {message}\033[0m")

            try:
                self.opponent_tactics = message.split('[tactics]')[1].split('[tactics end]')[0].strip()
                return
            except IndexError:
                logger.warning("Warning: No tactics found in the message. Retrying...")

        logger.warning("Warning: No tactics found in the message after 3 retries. Using previous tactics.")

    def render_system_message(self, scenario, opponent_id, causal_graph):
        system_prompt = load_prompt("opp_tactics_update")
        message = f"Your team name is {scenario.team_names[opponent_id]}\n\nYour team's task: {scenario.team_objectives[opponent_id]}\n\nScenario: {scenario.description}"
        if causal_graph:
            message += f"\n\nCausal Graph: {causal_graph}"
        message += f"\n\n{system_prompt}"
        system_message = SystemMessage(content=message)
        return system_message

    def render_human_message(self, events, scenario, opponent_id):
        observation = "chat log:\n"
        agent_names = scenario.team_affiliates[opponent_id]
        for event_type, content in events:
            if event_type != "onChat":
                continue
            split_index = content["onChat"].find('>')
            chatter, message = content["onChat"][1:split_index], content["onChat"][split_index + 2:]
            if chatter not in agent_names:
                continue
            observation += f"<{chatter}> {message}\n"

        observation += f"Previous tactics:\n{self.opponent_tactics}\n\n"

        return HumanMessage(content=observation)
