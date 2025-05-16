// Checks if you have a hoe and tills all nearby dirt blocks: await tillLand(bot, ["dirt"]);
async function tillLand(bot, lands = ["dirt"]) {
    const hoe = bot.inventory.items().find(item => item.name.includes('hoe'));
    await bot.equip(hoe, 'hand');
    const blocks = bot.findBlocks({
        matching: block => block && lands.includes(block.name),
        maxDistance: 32,
        count: 1000
    });
    for (const position of blocks) {
        await bot.pathfinder.goto(new GoalNear(position.x, position.y, position.z, 3));
        await bot.activateBlock(bot.blockAt(position));
    }
}

async function plantCrop(bot, crop, lands, directions) {
    var seeds = bot.inventory.items().find(item => item.name === crop);
    const blocks = bot.findBlocks({
        matching: block => block && lands.includes(block.name),
        maxDistance: 32,
        count: 1000
    });
    for (const position of blocks) {
        for (const direction of directions) {
            const blockOffset = bot.blockAt(position.add(direction));
            if (blockOffset.name === 'air') {
                await bot.pathfinder.goto(new GoalNear(position.x, position.y, position.z, 3));
                await bot.equip(seeds, 'hand');
                await bot.activateBlock(bot.blockAt(position));
            }
        }
    }
}

// Plants sweet berry bushes on nearby farmland or dirt blocks in a 32 block radius. If the bot does not have sweet berries, it will not plant them.
async function plantSweetBerryBushes(bot) {
    await plantCrop(bot, "sweet_berries", ["farmland", "dirt"], [new Vec3(0, 1, 0)]);
}

// Plants wheat seeds on nearby farmland blocks in a 32 block radius. If the bot does not have wheat seeds, it will not plant them.
async function plantWheatSeeds(bot) {
    await plantCrop(bot, "wheat_seeds", ["farmland"], [new Vec3(0, 1, 0)]);
}

// Plants potatoes on nearby farmland blocks in a 32 block radius. If the bot does not have potatoes, it will not plant them.
async function plantPotatoes(bot) {
    await plantCrop(bot, "potato", ["farmland"], [new Vec3(0, 1, 0)]);
}

// Plants carrots on nearby farmland blocks in a 32 block radius. If the bot does not have carrots, it will not plant them.
async function plantCarrots(bot) {
    await plantCrop(bot, "carrot", ["farmland"], [new Vec3(0, 1, 0)]);
}

// Plants beetroot seeds on nearby farmland blocks in a 32 block radius. If the bot does not have beetroot seeds, it will not plant them.
async function plantBeetrootSeeds(bot) {
    await plantCrop(bot, "beetroot_seeds", ["farmland"], [new Vec3(0, 1, 0)]);
}

// Plants cocoa beans on nearby jungle log blocks in a 32 block radius. If the bot does not have cocoa beans, it will not plant them.
async function plantCocoaBeans(bot) {
    await plantCrop(bot, "cocoa_beans", ["jungle_log"], [new Vec3(1, 0, 0), new Vec3(-1, 0, 0), new Vec3(0, 0, 1), new Vec3(0, 0, -1)]);
}

// Plants melon seeds on nearby farmland blocks in a 32 block radius. If the bot does not have melon seeds, it will not plant them.
async function plantMelonSeeds(bot) {
    await plantCrop(bot, "melon_seeds", ["farmland"], [new Vec3(0, 1, 0)]);
}

// Plants pumpkin seeds on nearby farmland blocks in a 32 block radius. If the bot does not have pumpkin seeds, it will not plant them.
async function plantPumpkinSeeds(bot) {
    await plantCrop(bot, "pumpkin_seeds", ["farmland"], [new Vec3(0, 1, 0)]);
}

// Plants sugar cane on nearby dirt or sand blocks in a 32 block radius. If the bot does not have sugar cane, it will not plant it.
async function plantSugarCane(bot) {
    await plantCrop(bot, "sugar_cane", ["dirt", "sand"], [new Vec3(0, 1, 0)]);
}

async function harvest(bot, pos, crop, goalNear, activateBlock, matching = undefined) {
    const crops = bot.findBlocks({
        matching: mcData.blocksByName[crop].id,
        useExtraInfo: matching,
        point: pos,
        maxDistance: 25,
        count: 20
    });
    if (crops.length === 0) {
      return;
    }
    const targets = [];
    for (let i = 0; i < crops.length; i++) {
        const target = bot.blockAt(crops[i]);
        targets.push(target);
    }
    await bot.collectBlock.collect(targets, {
      ignoreNoPath: true,
      count: targets.length,
      goalNear: goalNear,
      activateBlock: activateBlock,
    });
}

// Harvests sweet berry bushes in a 32 block radius around a target position. Note that sweet berry bushes need to be activated to be harvested.
async function harvestBerries(bot, pos) {
    await harvest(bot, pos, "sweet_berry_bush", true, true, block => block.getProperties().age > 1);
}

// Harvests wheat in a 32 block radius around a target position. Note that wheat needs to be broken to be harvested. Replanting should be done manually afterward to ensure the farm is sustainable.
// await harvestWheat(bot, new Vec3(0, -60, 0));
// await plantWheatSeeds(bot);
async function harvestWheat(bot, pos) {
    await harvest(bot, pos, "wheat", true, false, block => block.getProperties().age > 6);
}

// Harvests potatoes in a 32 block radius around a target position. Note that potatoes need to be broken to be harvested. Replanting should be done manually afterward to ensure the farm is sustainable.
// await harvestPotatoes(bot, new Vec3(0, -60, 0));
// await plantPotatoes(bot);
async function harvestPotatoes(bot, pos) {
    await harvest(bot, pos, "potatoes", true, false, block => block.getProperties().age > 6);
}

// Harvests carrots in a 32 block radius around a target position. Note that carrots need to be broken to be harvested. Replanting should be done manually afterward to ensure the farm is sustainable.
// await harvestCarrots(bot, new Vec3(0, -60, 0));
// await plantCarrots(bot);
async function harvestCarrots(bot, pos) {
    await harvest(bot, pos, "carrots", true, false, block => block.getProperties().age > 6);
}

// Harvests beetroot in a 32 block radius around a target position. Note that beetroot needs to be broken to be harvested. Replanting should be done manually afterward to ensure the farm is sustainable.
// await harvestBeetroot(bot, new Vec3(0, -60, 0));
// await plantBeetrootSeeds(bot);
async function harvestBeetroot(bot, pos) {
    await harvest(bot, pos, "beetroots", true, false, block => block.getProperties().age > 2);
}

// Harvests cocoa in a 32 block radius around a target position. Note that cocoa needs to be broken to be harvested. Replanting should be done manually afterward to ensure the farm is sustainable.
// await harvestCocoa(bot, new Vec3(0, -60, 0));
// await plantCocoaBeans(bot);
async function harvestCocoa(bot, pos) {
    await harvest(bot, pos, "cocoa", false, false, block => block.getProperties().age > 1);
}

// Harvests melons in a 32 block radius around a target position. Melon blocks sit next to the melon stem, so when the melon block is broken, the melon item is dropped, and the melon stem remains to regrow.
async function harvestMelons(bot, pos) {
    await harvest(bot, pos, "melon", false, false);
}

// Harvests pumpkins in a 32 block radius around a target position. Pumpkins are broken to be harvested, and the pumpkin stem remains to regrow.
async function harvestPumpkins(bot, pos) {
    await harvest(bot, pos, "pumpkin", false, false);
}

// Harvests sugar cane in a 32 block radius around the bot's position, 2 blocks above the ground y level, so the bottom sugar cane remains to regrow. Harvesting sugar cane will give you the sugar_cane item.
async function harvestSugarCane(bot, ground_y) {
    await harvest(bot, undefined, "sugar_cane", true, false, block => block.position.y === ground_y + 2);
}

async function equipBucket(bot) {
    const bucketId = mcData.itemsByName["bucket"].id;
    let buckets = bot.inventory.findInventoryItem(bucketId);
    if (!buckets) {
        bot.chat("No bucket in inventory.");
        return false;
    }
    await bot.equip(buckets, "hand");
    return true
}

// Equips a bucket and milks a nearby cow once. If the bot does not have a bucket or there is no cow, it will not milk the cow.
async function milkCow(bot) {
    const mobName = "cow";
    const entity = bot.nearestEntity(
      (entity) =>
          entity.name === mobName &&
          entity.position.distanceTo(bot.entity.position) < 48
    );
    if (!entity) {
        bot.chat(`No ${mobName} nearby, please explore first`);
        return;
    }
    if (await equipBucket(bot)) {
        await bot.pathfinder.goto(new GoalFollow(entity, 3), true);
        await bot.activateEntity(entity);
    }
}

// Destroys all nearby crops of a specific type in a 32 block radius.
async function destroyCrop(bot, crop) {
    const blockByName = mcData.blocksByName[crop];
    const blocks = bot.findBlocks({
      matching: [blockByName.id],
      maxDistance: 32,
      count: 1000
    });
    const targets = [];
    for (let i = 0; i < blocks.length; i++) {
        const target = bot.blockAt(blocks[i]);
        targets.push(target);
    }
    await bot.collectBlock.collect(targets, {
      ignoreNoPath: true,
      count: targets.length,
      goalNear: true,
    });
}