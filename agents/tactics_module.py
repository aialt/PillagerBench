import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from bench.scenario import Scenario
from voyager import Negotiator, Negotiation
from voyager.llm import create_llm, invoke_with_log
from voyager.prompts import load_prompt

logger = logging.getLogger(__name__)

class TacticsModule:
    def __init__(
            self,
            team_tactics=None,
            negotiator_model_name="gpt-4o",
            negotiator_temperature=0.7,
            negotiator_max_turns=6,
    ):
        self.team_tactics = team_tactics
        self.prev_team_tactics = ""
        self.negotiator_model_name = negotiator_model_name
        self.negotiator_temperature = negotiator_temperature
        self.negotiator_max_turns = negotiator_max_turns

        self.llm = create_llm(
            model_name=negotiator_model_name,
            temperature=negotiator_temperature,
            request_timeout=120,
        )

    def step(self, scenario, team_id, events, save_dir, *, chest_memory, causal_graph=None, opp_tactics=None):
        # load the tactics
        if self.team_tactics is not None:
            if events is not None:
                logger.info("Updating tactics based on events.")
                self.prev_team_tactics = self.team_tactics
                self.update_tactics(scenario, team_id, events, chest_memory=chest_memory, causal_graph=causal_graph, opp_tactics=opp_tactics)
            else:
                logger.info("Using tactics from config. Skipping tactics generation.")
        else:
            logger.info('Negotiating new tactics.')
            self.prev_team_tactics = self.team_tactics
            self.team_tactics = ""
            self.negotiate_tactics(scenario, team_id, self.negotiator_max_turns, save_dir, causal_graph=causal_graph)

        # save tactics to file
        with open(f"{save_dir}/tactics.json", 'w') as tactics_file:
            # noinspection PyTypeChecker
            json.dump(self.team_tactics, tactics_file, indent=4)

    def update_tactics(self, scenario: Scenario, team_id: int, events, *, chest_memory, causal_graph, opp_tactics):
        """
        Updates the tactics based on the events that have occurred.
        """
        messages = [
            self.render_system_message(scenario, team_id, causal_graph),
            self.render_human_message(events, chest_memory, opp_tactics),
        ]

        for _ in range(3):
            response = invoke_with_log(self.llm, messages, prefix="Tactics ")
            content = response.content

            if '<think>' in content and '</think>' in content:
                # Strip any thinking content from the response for reasoning models
                split_content = content.split('<think>')
                message = split_content[1].split('</think>')[1].strip()
            else:
                # Parsing the response based on the new structure
                message = content.strip()

            logger.info(f"\033[94mAI message: {message}\033[0m")

            try:
                self.team_tactics = message.split('[tactics]')[1].split('[tactics end]')[0].strip()
                return
            except IndexError:
                logger.warning("Warning: No tactics found in the message. Retrying...")

        logger.warning("Warning: No tactics found in the message after 3 retries. Using previous tactics.")

    def negotiate_tactics(self, scenario: Scenario, team_id: int, max_turns, save_dir, *, causal_graph):
        """
        Generates a tactics for the team to follow and sets self.team_tactics to the tactics.
        """
        logger.info('Negotiating tactics...')

        if scenario.description is None:
            raise ValueError("Scenario must be loaded before negotiating tactics")

        negotiator1 = Negotiator(
            team_id=team_id,
            scenario=scenario,
            causal_graph=causal_graph,
            model=self.negotiator_model_name,
            temperature=self.negotiator_temperature,
        )

        # hold a negotiation between players, where negotiator1 starts first
        negotiation = Negotiation(negotiator1, max_turns=max_turns, save_dir=save_dir,
                                  team_name=team_id)
        negotiation.simulate()
        self.team_tactics = negotiation.get_tactics()

    def render_system_message(self, scenario, team_id, causal_graph):
        system_prompt = load_prompt("tactics_update")
        message = f"Your team name is {scenario.team_names[team_id]}\n\nYour Task: {scenario.team_objectives[team_id]}\n\nScenario: {scenario.description}"
        if causal_graph:
            message += f"\n\nCausal Graph: {causal_graph}"
        message += f"\n\n{system_prompt}"
        system_message = SystemMessage(content=message)
        return system_message

    def render_human_message(self, events, chest_memory, opp_tactics):
        chat_messages = []
        error_messages = []
        damage_messages = []
        voxels = None
        inventory = None
        inventory_used = 0
        username = "unknown"
        other_username = "unknown"
        other_inventory = None
        other_inventory_used = 0
        assert events[-1][0] == "observe", "Last event must be observe"
        for i, (event_type, event) in enumerate(events):
            if event_type == "onChat":
                chat_messages.append(event["onChat"])
            elif event_type == "onError":
                error_messages.append(event["onError"])
            elif event_type == "onDamage":
                damage_messages.append(event["onDamage"])
            elif event_type == "observe":
                voxels = event["voxels"]
                inventory_used = event["status"]["inventoryUsed"]
                inventory = event["inventory"]
                username = event["status"]["name"]
            elif event_type == "otherObserve":
                other_inventory_used = event["status"]["inventoryUsed"]
                other_inventory = event["inventory"]
                other_username = event["status"]["name"]

        observation = ""

        if chat_messages:
            chat_log = "\n".join(chat_messages)
            observation += f"Chat log:\n{chat_log}\n\n"
        else:
            observation += f"Chat log: None\n\n"

        if voxels:
            observation += f"Nearby blocks: {', '.join(voxels)}\n\n"
        else:
            observation += f"Nearby blocks: None\n\n"

        observation += f"Chest memory: {chest_memory}\n\n"

        observation += f"{username}:\n"

        if inventory:
            observation += f"Inventory ({inventory_used}/36): {inventory}\n\n"
        else:
            observation += f"Inventory ({inventory_used}/36): Empty\n\n"

        observation += f"{other_username}:\n"

        if other_inventory:
            observation += f"Inventory ({other_inventory_used}/36): {other_inventory}\n\n"
        else:
            observation += f"Inventory ({other_inventory_used}/36): Empty\n\n"

        if opp_tactics:
            observation += f"Opponent tactics:\n{opp_tactics}\n\n"

        observation += f"Previous tactics:\n{self.team_tactics}\n\n"

        return HumanMessage(content=observation)
