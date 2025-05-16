import logging
import random
import time
from typing import Any

from bench.agent import Agent
from bench.agent_utils import run_threads
from bench.pillager_env import PillagerEnv
from bench.scenario import Scenario

logger = logging.getLogger(__name__)


class Random(Agent):
    name = "random"

    def __init__(self, **kwargs):
        self.save_dir = None
        self.agents = []
        self.result = None
        self.events = None
        self.scenario = None
        self.options = []
        self.last_events = None
        self.team_id = 0

    @property
    def programs(self):
        return {
            "mineBlock": ["await mineBlock(bot, blocks[Math.floor(Math.random() * blocks.length)], Math.floor(Math.random() * 10), bot.entity.position.offset(Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16)), Math.floor(Math.random() * 30) + 2);"],
            "placeItem": ["if (bot.inventory.items().length > 0) {await placeItem(bot, bot.inventory.items()[Math.floor(Math.random() * bot.inventory.items().length)]?.name, bot.entity.position.offset(Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16)));}"],
            "multiAgent": [],
            "killMob": ["if (mobs.length > 0) {await killMob(bot, mobs[Math.floor(Math.random() * mobs.length)]);}"],
            "giveToPlayer": ["if (bot.inventory.items().length > 0){await giveToPlayer(bot, bot.inventory.items()[Math.floor(Math.random() * bot.inventory.items().length)]?.name, players[Math.floor(Math.random() * players.length)], Math.floor(Math.random() * 10));}"],
            "mineflayer": [
                "await bot.pathfinder.goto(new GoalNear(bot.entity.position.offset(Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16)).x, bot.entity.position.offset(Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16)).y, bot.entity.position.offset(Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16)).z, Math.floor(Math.random() * 30) + 2));",
                "if (bot.inventory.items().length > 0){await bot.equip(bot.inventory.items()[Math.floor(Math.random() * bot.inventory.items().length)], 'hand');}",
                # "if (bot.heldItem) {await bot.consume();}",
                # "await bot.fish();",
                # "await bot.sleep(getRandomBlockData(bot));",
                "randomBlock = getRandomBlockData(bot); if (randomBlock){await bot.activateBlock(randomBlock);}",
                "await bot.lookAt(bot.entity.position.offset(Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16)));",
                "await bot.activateItem();",
                "mobname = mobs[Math.floor(Math.random() * mobs.length)];entity = bot.nearestEntity(entity => entity.name.toLowerCase() === mobname); if(entity){await bot.useOn(entity);}",
            ],
            "exploreUntil": [],
            "farm": [
                "await tillLand(bot);",
                "await plantSweetBerryBushes(bot);",
                "await plantWheatSeeds(bot);",
                "await plantCarrots(bot);",
                "await plantPotatoes(bot);",
                "await plantBeetrootSeeds(bot);",
                "await plantCocoaBeans(bot);",
                "await plantMelonSeeds(bot);",
                "await plantPumpkinSeeds(bot);",
                "await plantSugarCane(bot);",
                "await harvestBerries(bot, null);",
                "await harvestWheat(bot, null);",
                "await harvestCarrots(bot, null);",
                "await harvestPotatoes(bot, null);",
                "await harvestBeetroot(bot, null);",
                "await harvestCocoa(bot, null);",
                "await harvestMelons(bot, null);",
                "await harvestPumpkins(bot, null);",
                "await harvestSugarCane(bot, -61);",
                "await milkCow(bot);",
                "await destroyCrop(bot, blocks[Math.floor(Math.random() * blocks.length)]);",
            ],
            "smeltItem": ["if (bot.inventory.items().length > 0){await smeltItem(bot, bot.inventory.items()[Math.floor(Math.random() * bot.inventory.items().length)]?.name, 'coal', Math.floor(Math.random() * 10));}"],
            "useChest": [
                "await getItemFromChest(bot, bot.entity.position.offset(Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16)), Object.keys(mcData.itemsByName)[Math.floor(Math.random() * Object.keys(mcData.itemsByName).length)]);"
                "if (bot.inventory.items().length > 0){await depositItemIntoChest(bot, bot.entity.position.offset(Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16), Math.floor(Math.random() * 33 - 16)), bot.inventory.items()[Math.floor(Math.random() * bot.inventory.items().length)]?.name);}"
            ],
            "craftItem": ["await craftItem(bot, Object.keys(mcData.itemsByName)[Math.floor(Math.random() * Object.keys(mcData.itemsByName).length)], Math.floor(Math.random() * 10));"],
        }

    def pre_game(self, scenario: Scenario, team_id: int, last_events: list[Any]):
        self.scenario = scenario
        self.last_events = last_events
        self.team_id = team_id

        # Get all programs for the control primitives
        self.options = []
        for primitive in scenario.control_primitives:
            self.options += self.programs.get(primitive, [])

    def post_game(self, scenario: Scenario, team_id: int):
        pass

    def run(self, scenario: Scenario, team_id: int, agent_envs: list[PillagerEnv]):
        run_threads([self.run_agent for _ in range(scenario.num_agents_per_team)],
                    args=list(zip(agent_envs, self.last_events)))

    def run_agent(self, agent_env: PillagerEnv, last_events: list[Any]):
        for _ in range(10):
            blocks = str(last_events[0][1]["voxels"])
            mobs = str(list(last_events[0][1]["status"]["entities"].keys()))
            players = str(self.scenario.team_affiliates[self.team_id])

            agent_script = f"const blocks = {blocks}; const mobs = {mobs}; const players = {players}; let mobname = 'cow'; let randomBlock = null; let entity = null;"
            agent_script += '''function getRandomBlockData(bot) {const blocks = Object.keys(mcData.blocksByName);if (blocks.length === 0) return null;const randomBlockName = blocks[Math.floor(Math.random() * blocks.length)];const blockId = mcData.blocksByName[randomBlockName].id;const blockLocations = bot.findBlocks({matching: blockId,maxDistance: 32,count: 100});if (blockLocations.length === 0) return null;  const randomLocation = blockLocations[Math.floor(Math.random() * blockLocations.length)];const blockData = bot.blockAt(randomLocation);return blockData;}'''
            # agent_script += '''function getRandomDestination() {const destinations = ["hand", "head", "torso", "legs", "feet", "off-hand"];const randomIndex = Math.floor(Math.random() * destinations.length);return destinations[randomIndex];}'''

            for i in range(100):
                agent_script += random.choice(self.options)
                if i % 5 == 0:
                    agent_script += "await bot.waitForTicks(20);"

            last_events = agent_env.step(agent_script)
            # Stop if timeout
            if (0 < self.scenario.episode_timeout < time.time() - self.scenario.episode_start_time
                    and 0 < self.scenario.episode_start_time):
                break

        logger.info(f"Agent {agent_env.username} finished")
