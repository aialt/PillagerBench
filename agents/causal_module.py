import json
import logging
import re
from string import Template

from langchain_core.messages import HumanMessage
from langchain_core.prompts import HumanMessagePromptTemplate

from bench.scenario import Scenario
from voyager.control_primitives_context import load_control_primitives_context
from voyager.llm import create_llm, invoke_with_log
from voyager.prompts import load_prompt
from voyager.utils import fix_and_parse_json

logger = logging.getLogger(__name__)

class CausalModule:
    def __init__(
            self,
            causal_model_name="gpt-4o",
            causal_temperature=0.3,
            causal_graph=None,
    ):
        self.causal_model_name = causal_model_name
        self.causal_temperature = causal_temperature
        self.max_llm_answer_num = 2

        # Learned causal subgraph is represented as {action : [[causes],[effects]]}
        self.learned_causal_subgraph = {}

        if causal_graph:
            result = json.loads(causal_graph)
            for action, cause, effect in result:
                self.learned_causal_subgraph[action] = [cause, effect]

        self.llm = create_llm(
            model_name=causal_model_name,
            temperature=causal_temperature,
            request_timeout=120,
        )

    def step(self, scenario, team_id, result, save_dir):
        if len(self.learned_causal_subgraph) > 0:
            if result is not None:
                # Update causal graph
                logger.info("Updating causal graph based on events.")
                self.update_causal_graph(scenario, team_id, result)
            else:
                # Use the existing causal graph
                logger.info("Using causal graph from config. Skipping causal generation.")
        else:
            # First step, generate new causal graph
            logger.info('Generating new causal graph.')
            self.generate_new_causal_graph(scenario)

        # save tactics to file
        with open(f"{save_dir}/causal_graph.json", 'w') as causal_graph_file:
            # noinspection PyTypeChecker
            json.dump(self.get_causal_graph(), causal_graph_file, indent=4)

    def update_causal_graph(self, scenario: Scenario, team_id: int, result):
        # Create prompt
        programs = "\n\n".join(load_control_primitives_context(scenario.control_primitives))

        events_message = ""
        for i in range(scenario.num_agents_per_team):
            agent_name = scenario.agent_names[team_id][i]
            events = result[agent_name]["events"]
            for event_type, content in events:
                if event_type != "onChat":
                    continue
                split_index = content["onChat"].find('>')
                chatter, message = content["onChat"][1:split_index], content["onChat"][split_index + 2:]
                if chatter != agent_name:
                    continue
                events_message += f"Chat: {message}; Inventory: {content['inventory']}\n"

        prompt_template = Template(load_prompt("causal_update"))
        human_message_prompt = prompt_template.safe_substitute({
            "programs": programs,
            "scenario": scenario.description,
            "graph": self.get_causal_graph(),
            "events": events_message
        })
        human_message = HumanMessage(human_message_prompt)
        messages = [human_message]

        # Get LLM answer
        llm_result = self.get_llm_answer(messages)

        if llm_result is None:
            logger.warning("Causal AI inference failed. Cannot update causal graph.")
            return

        for action, cause, effect in llm_result:
            self.learned_causal_subgraph[action] = [cause, effect]

    def generate_new_causal_graph(self, scenario: Scenario):
        self.learned_causal_subgraph = {}

        # Create prompt
        prompt_template = load_prompt("causal_init")
        programs = "\n\n".join(load_control_primitives_context(scenario.control_primitives))
        human_message_prompt = HumanMessagePromptTemplate.from_template(prompt_template)
        human_message = human_message_prompt.format(programs=programs, scenario=scenario.description)
        messages = [human_message]

        # Get LLM answer
        result = self.get_llm_answer(messages)

        if result is None:
            logger.warning("Causal AI inference failed. Cannot generate new causal graph.")
            return

        for action, cause, effect in result:
            self.learned_causal_subgraph[action] = [cause, effect]

    def get_llm_answer(self, messages):
        for _ in range(self.max_llm_answer_num):
            try:
                response_text = invoke_with_log(self.llm, messages, prefix="Causal ").content
                logger.info(f"\033[94mCausal AI message: {response_text}\033[0m")
                return fix_and_parse_json(response_text)
            except Exception as e:
                logger.warning("\033[91mLLM inference failed:" + str(e) + '\033[0m')
                continue
        return None

    def get_causal_graph(self):
        return '\n'.join([f"Action: {key}; Cause: {value[0]}; Effect {value[1]}" for key, value in
                          self.learned_causal_subgraph.items()]) if len(self.learned_causal_subgraph) > 0 else None

    def from_causal_graph(self, causal_graph):
        pattern = re.compile(
            r'Action:\s*(?P<action>.*?)(?=\s*;\s*Cause:)'  # capture key until "; Cause:" appears
            r'\s*;\s*Cause:\s*(?P<cause>.*?)(?=\s*;\s*Effect)'  # capture value[0] until "; Effect" appears
            r'\s*;\s*Effect:?\s*(?P<effect>.*?)(?=\n|$)',  # capture value[1] until a newline or end-of-string
            re.DOTALL
        )

        results = [match.groupdict() for match in pattern.finditer(causal_graph)]
        for r in results:
            self.learned_causal_subgraph[r["action"]] = [r["cause"], r["effect"]]

