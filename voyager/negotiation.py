import logging

from voyager.llm import create_llm, invoke_with_log
from voyager.prompts import load_prompt

class Negotiator:
    def __init__(self, team_id, scenario, causal_graph=None, model="gpt-3.5-turbo", temperature=0.1):
        self.team_id = team_id
        self.scenario = scenario
        self.causal_graph = causal_graph
        self.model = model
        self.temperature = temperature

        self.llm = create_llm(
            model_name=model,
            temperature=temperature,
            request_timeout=120,
        )

        # Including both tasks in the system prompt
        system_prompt = load_prompt("negotiator")
        self.system_prompt = f"Your team name is {scenario.team_names[team_id]}\n\nYour Task: {scenario.team_objectives[team_id]}\n\nScenario: {scenario.description}"
        if causal_graph:
            self.system_prompt += f"\n\nCausal Graph: {causal_graph}"
        self.system_prompt += f"\n\n{system_prompt}"

        self.messages = []
        self.reset()

    def reset(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def generate_message(self):
        response = invoke_with_log(self.llm, self.messages, prefix="Negotiation ")
        content = response.content

        if '<think>' in content and '</think>' in content:
            # Strip any thinking content from the response for reasoning models
            split_content = content.split('<think>')
            inner_thought = split_content[1].split('</think>')[0].strip()
            message = split_content[1].split('</think>')[1].strip()
        else:
            # Parsing the response based on the new structure
            inner_thought = ""
            message = content.strip()
        
        return inner_thought, message

class Negotiation:
    def __init__(self, agent1, max_turns=6, save_dir='logs', team_name=None):
        self.agent1 = agent1
        self.max_turns = max_turns
        self.save_dir = save_dir
        self.team_name = team_name
        self.conversation_log = []
        self.tactics = None
        self.reset()
        self.logger = self.setup_custom_logger()
                            
    def reset(self):
        self.conversation_log = []
        self.tactics = None
        self.agent1.reset()

    def setup_custom_logger(self):
        """
        Set up a custom logger with the given name and log file.
        """
        filename = 'negotiation' if self.team_name is None else f'negotiation_{self.team_name}'
        log_file = f'{self.save_dir}/{filename}.ansi'

        formatter = logging.Formatter(fmt='%(message)s')
        handler = logging.FileHandler(log_file, mode='w')  # Change to 'a' if you want to append
        handler.setFormatter(formatter)

        logger = logging.getLogger('negotiation')
        # Clear existing handlers from previous runs
        for h in logger.handlers:
            logger.removeHandler(h)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        
        def log_and_print(message, print_flag=False):
            logger.info(message)
            if print_flag: print(message)
        return log_and_print

    def _display_message(self, log, print_flag=False):
        # Define the color codes
        class Color:
            RED = '\033[91m'
            PINK = '\033[95m'
            BLUE = '\033[94m'
            LIGHT_BLUE = '\033[96m'
            LIGHT_GREEN = '\033[92m'
            GREEN = '\033[92m'
            DARK_GREEN = '\033[32m'
            RESET = '\033[0m'
        
        thought, message = log

        if len(thought) > 0:
            self.logger(f"{Color.LIGHT_BLUE}(Thought): {thought}{Color.RESET}",  print_flag=print_flag)
        self.logger(f"{Color.BLUE}(Message): {message}{Color.RESET}\n",  print_flag=print_flag)

    def simulate(self):
        if len(self.conversation_log) > 0:
            raise Exception("Conversation has already been simulated. Use display() to see the conversation. Or use reset() to start a new conversation.")

        last_tactics = None
        for turn in range(self.max_turns):
            thought, message = self.agent1.generate_message()

            self.conversation_log.append((thought, message))

            # Live display of conversation based on the flag
            self._display_message(self.conversation_log[-1])

            try:
                last_tactics = message.split('[tactics]')[1].split('[tactics end]')[0].strip()
                break
            except IndexError:
                self.logger("Warning: No tactics found in the message.")

        # Extract the tactics from the conversation log
        if last_tactics is None:
            raise Exception("Negotation failure. Tactics accepted but no tactics was found. Please try again.")

        self.tactics = last_tactics
        self.logger(f"Tactics:\n{self.tactics}\n")

    def get_tactics(self):
        if self.tactics is None:
            raise Exception("Conversation has not been simulated. Use simulate() to simulate the conversation.")
        return self.tactics