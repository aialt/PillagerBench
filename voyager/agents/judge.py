from langchain.schema import HumanMessage, SystemMessage

from voyager.llm import create_llm, invoke_with_log
from voyager.prompts import load_prompt
from voyager.utils.json_utils import fix_and_parse_json


class JudgeAgent:
    def __init__(
        self,
        model_name="gpt-3.5-turbo",
        temperature=0,
        request_timeout=120,
        mode="auto",
        logger=None,
        chat_log=True,
        execution_error=False,
    ):
        self.llm = create_llm(model_name, temperature, request_timeout)
        assert mode in ["auto", "manual"]
        self.mode = mode
        self.logger = logger
        self.chat_log = chat_log
        self.execution_error = execution_error

    def render_system_message(self):
        system_message = SystemMessage(content=load_prompt("judge"))
        return system_message

    def render_human_message(self, *, events, task, tactics, scenario, context, chest_observation):
        """
        args:
            task: a dictionary of task for each agent in the form of {agent_name: task}
        """

        chat_messages = []
        error_messages = []
        # FIXME: damage_messages is not used
        damage_messages = []
        assert events[-1][0] == "observe", "Last event must be observe"
        for i, (event_type, event) in enumerate(events):
            if event_type == "onChat":
                chat_messages.append(event["onChat"])
            elif event_type == "onError":
                error_messages.append(event["onError"])
                # self.logger(f"\033[31mCritic Agent: Error occurs {event['onError']}\033[0m")
                # return None # WHY SHOULD THIS RETURN??
            elif event_type == "onDamage":
                damage_messages.append(event["onDamage"])
            elif event_type == "observe":
                biome = event["status"]["biome"]
                time_of_day = event["status"]["timeOfDay"]
                voxels = event["voxels"]
                entities = event["status"]["entities"]
                health = event["status"]["health"]
                hunger = event["status"]["food"]
                position = event["status"]["position"]
                equipment = event["status"]["equipment"]
                inventory_used = event["status"]["inventoryUsed"]
                inventory = event["inventory"]
                username = event["status"]["name"]
                assert i == len(events) - 1, "observe must be the last event"
            elif event_type == "otherObserve":
                other_inventory_used = event["status"]["inventoryUsed"]
                other_inventory = event["inventory"]
                other_username = event["status"]["name"]

        observation = ""

        # if self.execution_error:
        #     if error_messages:
        #         error = "\n".join(error_messages)
        #         observation += f"Execution error:\n{error}\n\n"
        #     else:
        #         observation += f"Execution error: No error\n\n"

        if self.chat_log:
            if chat_messages:
                chat_log = "\n".join(chat_messages)
                observation += f"Chat log:\n{chat_log}\n\n"
            else:
                observation += f"Chat log: None\n\n"

        # observation += f"Biome: {biome}\n\n"

        # observation += f"Time: {time_of_day}\n\n"

        if voxels:
            observation += f"Nearby blocks: {', '.join(voxels)}\n\n"
        else:
            observation += f"Nearby blocks: None\n\n"

        observation += chest_observation

        # observation += f"Health: {health:.1f}/20\n\n"
        # observation += f"Hunger: {hunger:.1f}/20\n\n"

        # observation += f"Position: x={position['x']:.1f}, y={position['y']:.1f}, z={position['z']:.1f}\n\n"

        # observation += f"Equipment: {equipment}\n\n"

        observation += f"{username}:\n"

        observation += f"Task: {task[username]}\n"

        if inventory:
            observation += f"Inventory ({inventory_used}/36): {inventory}\n\n"
        else:
            observation += f"Inventory ({inventory_used}/36): Empty\n\n"

        observation += f"{other_username}:\n"

        observation += f"Task: {task[other_username]}\n"

        if other_inventory:
            observation += f"Inventory ({other_inventory_used}/36): {other_inventory}\n\n"
        else:
            observation += f"Inventory ({other_inventory_used}/36): Empty\n\n"

        observation += f"Scenario: {scenario}\n\n"

        observation += f"tactics:\n{tactics}\n\n"

        if context:
            observation += f"Context: {context}\n\n"
        else:
            observation += f"Context: None\n\n"

        self.logger(f"\033[31m****Judge Agent human message****\n{observation}\033[0m")
        return HumanMessage(content=observation)

    # def human_check_task_success(self):
    #     confirmed = False
    #     success = False
    #     critique = ""
    #     while not confirmed:
    #         success = input("Success? (y/n)")
    #         success = success.lower() == "y"
    #         critique = input("Enter your critique:")
    #         print(f"Success: {success}\nCritique: {critique}")
    #         confirmed = input("Confirm? (y/n)") in ["y", ""]
    #     return success, critique

    def ai_check_task_success(self, messages, max_retries=5):
        if max_retries == 0:
            self.logger(
                "\033[31mFailed to parse Judge Agent response. Consider updating your prompt.\033[0m"
            )
            return False, ""

        if messages[1] is None:
            return False, ""

        critic = invoke_with_log(self.llm, messages, prefix="Judge ").content
        self.logger(f"\033[31m****Judge Agent ai message****\n{critic}\033[0m")

        # fix this 
        try:
            response = fix_and_parse_json(critic)
            
            # success = {}
            critique = {}
            emeralds = {}
            for name, res in response.items():
                if name == "reasoning":
                    continue

                # assert res["success"] in [True, False]
                assert isinstance(res["emeralds"], int)
                emeralds[name] = res["emeralds"]
                # success[name] = res["success"]
                if "critique" not in res:
                    critique[name] = ""
                else:
                    critique[name] = res["critique"]
                
            return emeralds, critique
        except Exception as e:
            self.logger(f"\033[31mError parsing judge response: {e} Trying again!\033[0m")
            return self.ai_check_task_success(
                messages=messages,
                max_retries=max_retries - 1,
            )