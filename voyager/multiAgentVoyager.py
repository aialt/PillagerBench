import json
import threading

from voyager import Voyager
from voyager.llm import invoke_with_log
from voyager.negotiation import Negotiation, Negotiator
import time
import voyager.utils as U
import copy
from datetime import datetime
import requests

class MultiAgentVoyager:
    
    def __init__(self,
                 num_agents=2,
                 server_port=3003,
                 usernames=["Ryn", "Raze", "Byte", "Blink"],
                 judge_username="Judy",
                 scenario_file=None,
                 save_dir=None,
                 replay=False,
                 critic_mode="auto",
                 tactics_mode="auto",
                 team_tactics=None,
                 continuous=True,
                 episode_timeout=120,
                 num_episodes=3,
                 negotiator_model_name="gpt-4",
                 negotiator_temperature=0.7,
                 skinurls = [
            "https://images2.imgbox.com/60/3d/2bJnlM8U_o.png", # player 1 skin
            "https://images2.imgbox.com/a7/6c/hZRGGRAS_o.png" # player 2 skin
        ],
                 options={}
                 ):

        self.scenario_file = scenario_file
        self.scenario_description = None
        self.scenario_code = None
        self.critic_mode = critic_mode
        self.continuous = continuous
        self.tactics_mode = tactics_mode
        self.team_tactics = team_tactics
        self.agents = []
        self.judge = None
        self.usernames = usernames
        self.judge_username = judge_username
        self.num_episodes = num_episodes
        self.negotiator_model_name = negotiator_model_name
        self.negotiator_temperature = negotiator_temperature
        self.skinurls = skinurls
        self.chest_memory = {}
        self.episode = 0
        self.load_from_save = False
        self.teams = None
        self.team_members = None
        self.replay = replay

        assert critic_mode in ["auto", "manual"]
        assert tactics_mode in ["auto", "manual"]
        if self.continuous:
            assert isinstance(self.num_episodes, int) and self.num_episodes > 0

        if self.tactics_mode == "manual":
            if team_tactics is None:
                raise ValueError("Tactics mode is manual but no team tactics were provided")
            if not isinstance(team_tactics, dict):
                raise ValueError("Team tactics must be a dictionary of strings")
            self.team_tactics = team_tactics
        
        # load game save directory if it exists
        if save_dir is not None and U.f_not_empty(save_dir):
            print("Provided save directory exists. Loading game...")
            self.save_dir = save_dir

            # recover tactics
            try:
                with open(f"{self.save_dir}/tactics.json", 'r') as tactics_file:
                    self.team_tactics = json.load(tactics_file)
                if tactics_mode == "auto":
                    print("Warning: tactics mode is auto but tactics were found in save directory. Overwriting with saved tactics...")
            except FileNotFoundError:
                raise("No tactics found in save directory")
            
            self.load_from_save = True
        
        # create new game save directory
        else:
            if save_dir is None:
                self.save_dir = f"saves/game_save_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                self.save_dir = save_dir
            U.f_mkdir(self.save_dir)
            U.f_mkdir(f"{self.save_dir}/episodes")

        # create judge
        self.judge = Voyager(
            server_port=server_port,
            username=self.judge_username,
            ckpt_dir=f"{self.save_dir}/{self.judge_username}_ckpt",
            episode_timeout=episode_timeout,
            **options
        )
        self.judge.env.reset()

        # create agents
        for i in range(num_agents):
            username=self.usernames[i]
            ckpt_dir=f"{self.save_dir}/{username}_ckpt"

            agent = Voyager(
                username=username,
                server_port=str(server_port+1+i),
                ckpt_dir=ckpt_dir,
                episode_timeout=episode_timeout,
                **options
            )
            self.agents.append(agent)

        # # set voyager skins
        # for i, agent in enumerate(self.agents):
        #     agent.env.reset()
        #     agent.env.step(
        #         U.skins_commands(self.skinurls[i])
        # )

        # time.sleep(1)

    def run_threads(self, target, args=None, include_judge=False, shared_args=False):
        """
        Runs target function in parallel for each agent. args is a dictionary of arguments to pass to each thread, where the key is the agent's username.

        For example,
        args = {'Voyager3000': {'arg1': 1, 'arg2': 2}, 'Voyager3001': {'arg1': 3, 'arg2': 4}}
        """
        agents = self.agents + [self.judge] if include_judge else self.agents
        if args is None: args = {agent.username: {} for agent in agents}
        if shared_args: args = {agent.username: args for agent in agents}

        results = {}
        threads = []
        for agent in agents:
            result = {}
            thread = threading.Thread(target=target, args=(agent, result), kwargs=args[agent.username], daemon=True)
            results[agent.username] = result
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        return results
    
    def reset_agents(self, mode='soft', timeout=10):
        args = {agent.username: {'options': {'mode': mode, 'wait_ticks': agent.env_wait_ticks}} for agent in self.agents}
        self.run_threads(lambda agent, _, options: agent.env.reset(options=options), args=args)
        time.sleep(2)

    def save_scenario(self, save_options):
        """
        Saves the current scenario to a json file. The scenario is saved as a dictionary with the following keys:
        - block_positions: a dictionary of block types and their positions
        - spawn_locations: a dictionary of agent usernames and their spawn locations
        - chest_contents: a string of the chest contents in minecraft format
        """
        print('Saving scenario...')

        if len(self.agents) == 0:
            raise('At least one agent must be initialized to save scenario')

        scenario_block_types = save_options['scenario_block_types']
        file_name = save_options['file_name']
        center_position = save_options['center_position']
        remove_blocks = save_options['remove_blocks']

        # set file_name
        if self.scenario_file != file_name:
            print(f'Warning: scenario_file does not match file_name, using {file_name}')
        file_name = "scenarios/" + file_name

        def extract_block_positions(events):
            block_types = scenario_block_types
            block_positions = {block: [] for block in block_types}

            for event in events:
                if event[0] == 'onChat':
                    message = event[1]['onChat']
                    # Checking each block type
                    for block in block_types:
                        if block in message:
                            # Extracting positions
                            positions = message.split(f'{block}: ')[-1].replace('),(', ');(').split(';')
                            for pos in positions:
                                if not pos.strip():  # Check if the position is an empty string
                                    continue
                                x, y, z = map(int, pos.strip('()').split(', '))
                                coord_dict = {'x': x, 'y': y, 'z': z}  # Convert coords to dictionary format
                                block_positions[block].append(coord_dict)

            # Removing block types with no positions found
            block_positions = {k: v for k, v in block_positions.items() if v}
            return block_positions

        # self.judge.env.reset(
        #         options={
        #             "mode": "hard",
        #             "wait_ticks": self.judge.env_wait_ticks,
        #         }
        #     )
        
        x, y, z = center_position['x'], center_position['y'], center_position['z']

        # Remove blocks of type scenario_block_types so they don't interfere with the scenario
        if remove_blocks:
            input(f"Center position is set to {center_position}. Blocks of type {scenario_block_types} will be deleted nearby. Press enter to continue...")
            print("Removing blocks...\n")
            self.judge.env.step(
                f"await bot.chat('/tp {x} {y} {z}');"
                + U.remove_blocks_commands(scenario_block_types, center_position),
                programs=self.judge.skill_manager.programs,
            )

        # Save blocks of type scenario_block_types
        input(f"Construct the scenario. Blocks of type {scenario_block_types} will be saved. Press enter when done...")
        print("Saving blocks...\n")
        events = self.judge.env.step(
            f"bot.chat('/tp {x} {y} {z}');"
            + f"await getBlockPositions(bot, {U.json_dumps(scenario_block_types)}, {U.json_dumps(center_position)})", # should be able to specify center square of save area
            programs=self.judge.skill_manager.programs,
        )

        block_positions = extract_block_positions(events)

        # save block_positions as well as default spawn locations and chest contents
        json_contents = {
            'description': 'There is a chest with a diamond pickaxe.',
            'secret_description': 'Agents do not see this description, just for information',
            'tasks': {self.usernames[0]: 'mine diamond', self.usernames[1]: 'mine iron'},
            'center_position': center_position,
            'block_positions': {'facing': 'north', **block_positions},
            'spawn_locations': {self.usernames[0]: {'x':x+1, 'y': y, 'z': z+1}, self.usernames[1]: {'x':x-1, 'y': y, 'z': z-1}},
            'reward_item_name': ['diamond'],
            'chest_contents': {'diamond_pickaxe':1},
        }
        U.custom_dump(json_contents, file_name)
        print('Scenario saved in ', file_name)
        self.judge.close()

    def load_scenario(self, reset='soft'):

        # set file_name
        file_name = "scenarios/" + self.scenario_file

        try: 
            json_contents = U.json_load(file_name)
            print(f'Loading {self.scenario_file}...')
        except FileNotFoundError:
            raise('No scenario file found')

        self.scenario_description = json_contents['description']
        tasks = json_contents['tasks']
        center_position = json_contents['center_position']
        block_positions = json_contents['block_positions']
        spawn_locations = json_contents['spawn_locations']
        chest_contents = U.parse_chest_contents(json_contents['chest_contents'])
        scenario_block_types = list(block_positions.keys())
        scenario_block_types.remove('facing')
        self.chest_memory = {}
        self.teams = json_contents.get('teams', None)
        self.team_members = json_contents.get('team_members', None)

        # set agent tasks
        for i, agent in enumerate(self.agents):
            agent.task = tasks[agent.username]
            agent.team = self.team_members[agent.username]
            agent.reward_item_names = self.teams[agent.team]["reward_item_names"]

        # set judge task to all agents tasks
        self.judge.task = tasks

        # if .js with same filename exists, load it
        if U.f_exists(file_name.replace('.json', '.js')):
            self.scenario_code = U.load_text(file_name.replace('.json', '.js'))
        else:
            print('Warning: No scenario code file found')

        # clear inventory for both agents
        if len(self.agents) == 0:
            raise('At least one agent must be initialized to load scenario')
        self.reset_agents(mode='hard')

        x, y, z = center_position['x'], center_position['y'], center_position['z']

        # spawn bots, replace blocks, and fill chest
        self.judge.env.step(
            f"bot.chat('/gamemode spectator {self.judge_username}');"
            + f"bot.chat('/tp {self.judge_username} {x} {y+20} {z}');" # move this into a helper?
            + f"bot.chat('/gamerule randomTickSpeed 3');"
            + f"bot.chat('/gamerule spawnRadius 0');"
            + U.remove_drops_commands()
            + (U.remove_blocks_commands(scenario_block_types, center_position) if reset == 'hard' else '')
            + U.spawn_commands(self.usernames, spawn_locations)
            + U.add_block_commands(block_positions)
            + U.chest_commands(block_positions, chest_contents),
            programs=self.judge.skill_manager.programs,
        )
        # events[-1][1]["inventory"] = new_events[-1][1]["inventory"]
        # events[-1][1]["voxels"] = new_events[-1][1]["voxels"]

        if self.scenario_code is not None:
            self.judge.env.step(self.scenario_code)

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
        for agent in self.agents + [self.judge]:
            agent.action_agent.chest_memory = self.chest_memory

    def check_task_success(self, events, max_retries=5):
        
        def ai_check_task_success(agent, result, events):
            if agent.username == self.judge_username:
                critic_agent = agent.judge_agent
            else:
                critic_agent = agent.critic_agent

            human_message = critic_agent.render_human_message(
                events=events,
                task=agent.task,
                scenario=self.scenario_description,
                tactics=self.team_tactics[agent.team],
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

            if agent.username == self.judge_username:
                emeralds, critique = critic_response
                success = None
            else:
                success, critique = critic_response
                emeralds = None

            result.update({'success': success, 'critique': critique})

        def human_check_task_success():
            results = {agent.username: {} for agent in self.agents}
            # log critic human critic messages
            for agent in self.agents:
                agent.critic_agent.render_human_message(
                    events=events[agent.username]['events'],
                    task=agent.task,
                    scenario=self.scenario_description,
                    tactics=self.team_tactics[agent.team],
                    context=agent.context,
                    chest_observation=agent.action_agent.render_chest_observation(),
                )
            # collect critiques about agents
            for agent in self.agents:
                confirmed = False
                success = False
                critique = ""
                while not confirmed:
                    success = input(f"{agent.username} Success? (y/n)")
                    success = success.lower() == "y"
                    critique = input("Enter your critique:")
                    print(f"Success: {success}\nCritique: {critique}")
                    confirmed = input("Confirm? (y/n)") in ["y", ""]
                results[agent.username].update({'success': success, 'critique': critique})
            return results

        if self.critic_mode == "manual":
            return human_check_task_success()
        
        return self.run_threads(ai_check_task_success, events, include_judge=False)
        
    def save_episode(self, results):
        U.dump_json(results, f"{self.save_dir}/episodes/episode{self.episode}/code.json")

    def load_episode(self, episode): 
        if not isinstance(episode, int):
            raise ValueError("episode must be an integer")
        
        file_name = f"{self.save_dir}/episodes/episode{episode}/code.json"
        json_contents = U.json_load(file_name)
        return json_contents
    
    # def replay_episode(self, episode):
    #     if not isinstance(episode, int):
    #         raise ValueError("episode must be an integer")

    #     episode_results = self.load_episode(episode)
    #     self.run_threads(env_step, args=episode_results)
    
    def run_episode(self, episode=None, reload=True, reset='soft'):
        # get ai_message and parse
        def get_ai_message_parse(agent, result):
            if agent.action_agent_rollout_num_iter < 0:
                raise ValueError("Agent must be reset before stepping")
            ai_message = invoke_with_log(agent.action_agent.llm, agent.messages, prefix="Action ")
            agent.logger(f"\033[34m****Action Agent ai message****\n{ai_message.content}\033[0m")
            agent.conversations.append(
                (agent.messages[0].content, agent.messages[1].content, ai_message.content)
            )
            parsed_result = agent.action_agent.process_ai_message(message=ai_message)
            result.update({'parsed_result': parsed_result})

        # do env.step
        def env_step(agent, result, parsed_result):
            if not isinstance(parsed_result, dict):
                assert isinstance(parsed_result, str)
                print('parsed_result', parsed_result)
                agent.recorder.record([], agent.task) 
                agent.logger(f"\033[34m{parsed_result} Trying again!\033[0m")

            code = parsed_result["program_code"] + "\n" + parsed_result["exec_code"]
            events = agent.env.step(
                f"await saveRewards(bot, {U.json_dumps(agent.reward_item_names)}, '{self.save_dir}/episodes/episode{self.episode}');"
                + code,
                programs=agent.skill_manager.programs,
            )
            agent.recorder.record(events, agent.task) # what is this for??
            self.update_chest_memory(events[-1][1]["nearbyChests"])
            result.update({'events': events})

        # update messages for next round
        def update_agent(agent, result, parsed_result, events, success, critique):
            new_skills = agent.skill_manager.retrieve_skills(
                query=agent.context
                + "\n\n"
                + agent.action_agent.summarize_chatlog(events)
            )
            system_message = agent.action_agent.render_system_message(skills=new_skills)
            human_message = agent.action_agent.render_human_message(
                events=events,
                code=parsed_result["program_code"],
                task=agent.task,
                tactics=self.team_tactics[agent.team],
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
                or success
            )
            info = {
                "task": agent.task,
                "success": success,
                "conversations": agent.conversations,
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
            result.update({'messages': agent.messages, 'done': done, 'info': info})

        # replace chat events with those from the agent who lived longest and save both players observations
        # note: this is a hacky solution to a problem that should be fixed in the future
        def fix_chat_events(events):
            # collect all chat events for each agent
            chat_events = {agent.username: [] for agent in self.agents}
            other_events = {agent.username: [] for agent in self.agents}
            for agent in self.agents:
                other_agents = [a for a in self.agents if a != agent]
                if 'events' not in events[agent.username]:
                    continue
                for (event_type, event) in events[agent.username]['events']:
                    if event_type == 'onChat':
                        chat_events[agent.username].append((event_type, event))
                    # record both agents observations for reading inventory etc
                    elif event_type == 'observe':
                        for other_agent in other_agents:
                            other_events[other_agent.username].insert(0, ('otherObserve', event))
                        other_events[agent.username].append((event_type, event))
                    else:
                        other_events[agent.username].append((event_type, event))
            # copy in longest thread of chats
            longest_thread = max(chat_events.values(), key=len)
            new_events = {agent.username: {'events': longest_thread + other_events[agent.username]} for agent in self.agents}

            # copy one of the agents events for the judge
            new_events[self.judge_username] = new_events[self.agents[0].username]

            return new_events

        # reset for both agents and load scenario
        if reload:
            self.load_scenario(reset=reset)
            # time.sleep(3) # wait for voyagers and scenario to load
        
        # if a specific episode is provided, look for tactics and play it
        # ideally this should be moved to a different function (except env_step should be moved too)
        if episode is not None:
            if not isinstance(episode, int):
                raise ValueError("episode must be an integer")
            
            episode_results = self.load_episode(episode)
            self.run_threads(env_step, args=episode_results)
            self.reset_agents()
            return
        
        # get ai_message and parse in parallel
        print('get_ai_message_parse')
        parsed_results = self.run_threads(get_ai_message_parse)

        # save episode
        self.save_episode(parsed_results)

        # do env.step in parallel`
        print('env_step')
        events = self.run_threads(env_step, args=parsed_results)
        self.reset_agents()

        # check for task success
        print('check_task_success')
        events = fix_chat_events(events)
        critic_response = self.check_task_success(events)

        print(critic_response)

        # update agents (note this function does not need to be run with threads; could add a flag to just iterate)
        results = self.run_threads(update_agent, args={
            agent.username: {
                **parsed_results[agent.username],
                **events[agent.username], 
                **critic_response[agent.username],
                # 'tactics_critique': critic_response[self.judge.username]['critique'][agent.username],
                # 'emeralds': critic_response[self.judge.username]['emeralds'][agent.username],

            } for agent in self.agents}
        )

        return results

    def negotiate_tactics(self, team, max_turns=8):
        """
        Generates a tactics for the team to follow and sets self.tactics to the tactics.
        """
        print('Negotiating tactics...')
        
        if self.scenario_description is None:
            raise ValueError("Scenario must be loaded before negotiating tactics")

        agents = [agent for agent in self.agents if agent.team == team]
        agent1 = agents[0]
        agent2 = agents[1]

        negotiator1 = Negotiator(
            name=agent1.username,
            task=agent1.task,
            other_name=agent2.username,
            other_task=agent2.task,
            scenario=self.scenario_description,
            model=self.negotiator_model_name,
            temperature=self.negotiator_temperature,
        )
        negotiator2 = Negotiator(
            name=agent2.username,
            task=agent2.task,
            other_name=agent1.username,
            other_task=agent1.task,
            scenario=self.scenario_description,
            model=self.negotiator_model_name,
            temperature=self.negotiator_temperature,
        )

        # hold a negotiation between players, where negotiator1 starts first
        negotiation = Negotiation(negotiator1, negotiator2, max_turns=max_turns, save_dir=self.save_dir, team_name=team)
        negotiation.simulate()
        self.team_tactics[team] = negotiation.get_tactics()

    def run(self):

        if self.load_from_save:
            input("Warning: loaded from saved directory. Continuing may overwrite saved files. Press enter to continue...")

        self.load_scenario(reset='hard')
        
        # load the tactics
        if self.tactics_mode == "auto":
            if self.team_tactics is not None:
                print("Warning: tactics_mode is 'auto' but tactics are provided. skipping tactics generation.")
            else:
                print('Negotiating tactics...')
                self.team_tactics = {}
                for team in self.teams.keys():
                    self.negotiate_tactics(team)

        # save tactics to file
        with open(f"{self.save_dir}/tactics.json", 'w') as tactics_file:
            json.dump(self.team_tactics, tactics_file, indent=4)

        # set agent tasks and tactics
        self.run_threads(lambda agent, _, args: agent.reset(task=agent.task, **args), args={'args': {
            'tactics': self.team_tactics,
            'scenario': self.scenario_description,
            'context': "",
            'reset_env': False,}}, shared_args=True)

        replay = self.replay
        done = False
        while not done or replay:
            if replay:
                print('Repeating episode...')
                self.run_episode(episode=self.episode, reload=True, reset='soft')
            else:
                U.f_mkdir(f"{self.save_dir}/episodes/episode{self.episode}")

                # dont load episode if its already loaded
                reload = False if self.episode == 0 else True
                results = self.run_episode(reload=reload, reset='soft')

                # If all tasks were successful, stop
                # agent_successes = [result['info']['success'] for result in results.values()]
                # success = all(agent_successes)

                # # stop episode from ending
                # success = False
                
                # Print successes
                # for agent in self.agents:
                #     print(f"{agent.username} {{emeralds: {results[agent.username]['info']['emeralds']}}}")

                # save emerald values
                # U.json_dump({agent.username: results[agent.username]['info']['emeralds'] for agent in self.agents}, f"{self.save_dir}/episodes/episode{self.episode}/emeralds.json")

                # if success:
                #     user_response = input("Episode success. Press enter to close or 'r' to repeat...")
                #     if user_response == 'r': 
                #         replay = True
                #     else: 
                #         break
            
            # if not continuous mode wait to continue
            if self.continuous:
                self.episode += 1
                if self.episode == self.num_episodes:
                    done = True

            else:
                user_response = input("Press enter to continue or 'r' to repeat...")
                if user_response == 'r':
                    replay = True
                else:
                    replay = False
                    self.episode += 1 # only increment if not replaying

        print('Quitting...') 
    
    def close(self):
        server = self.judge.env.server
        res = requests.post(f"{server}/stop")
        for agent in self.agents + [self.judge]:
            agent.env.mineflayer.stop()
        
        # killing voyagers
        # self.agents[0].close()
        # for agent in self.agents:
        #     agent.close()





    # def run_episode(self, tasks, tactics="", context=""):
    #     results = []
    #     threads = []

    #     # Start threads to run rollouts concurrently
    #     for i, agent in enumerate(self.agents):
    #         task = tasks[i]
    #         result = {}
    #         thread = threading.Thread(target=self.step, args=(agent, result, task, tactics, context), daemon=True)
    #         threads.append(thread)
    #         results.append(result)
    #         thread.start()

    #     # Wait for all threads to finish
    #     for thread in threads:
    #         thread.join()

    #     # TODO: terminate threads that don't complete and update results to indicate timeout
    #     # time.sleep(45)
    #     # self.load_scenario(self.scenario)
    #     # for i, agent in enumerate(self.agents):
    #     #     agent.env.reset(
    #     #         options={
    #     #             "mode": "hard",
    #     #             "wait_ticks": 80,
    #     #         }
    #     #     )

    #     print('threads finished')
            
    #     return results

    # def step(self, agent, result, task, tactics, context):
    #     # resetting because every step is a new episode
    #     agent.reset(
    #         task=task, 
    #         tactics=tactics,
    #         context=context, 
    #         reset_env=False)
    #     messages, reward, done, info = messages, reward, done, info = agent.step()
    #     result.update({"messages": messages, "reward": reward, "done": done, "info": info})