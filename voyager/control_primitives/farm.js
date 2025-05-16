async function tillLand(bot, lands = ["dirt"]) {
    // Check if the bot has a hoe in its inventory
    const hoe = bot.inventory.items().find(item => item.name.includes('hoe'));
    if (!hoe) {
        bot.chat("No hoe in inventory.");
        return;
    }

    // Equip the hoe
    await bot.equip(hoe, 'hand');

    // Find all land blocks within a maximum distance of 32
    const blocks = bot.findBlocks({
        matching: block => block && lands.includes(block.name),
        maxDistance: 32,
        count: 1000
    });

    // For each block in the filtered list, move to the block and till it
    let tilled = 0;
    for (const position of blocks) {
        // Make sure the block above is air
        const blockAbove = bot.blockAt(position.offset(0, 1, 0));
        if (blockAbove.name !== 'air') {
            continue;
        }
        await bot.pathfinder.goto(new GoalNear(position.x, position.y, position.z, 3));
        await bot.activateBlock(bot.blockAt(position));
        tilled++;
    }
    if (tilled > 0) {
        bot.chat(`All available land has been tilled.`);
    }
}


async function plantCrop(bot, crop, lands, directions) {
    // Check if the bot has seeds in its inventory
    var seeds = bot.inventory.items().find(item => item.name === crop);
    if (!seeds) {
        bot.chat(`No ${crop} in inventory.`);
        _farmFailCount++;
        if (_farmFailCount > 10) {
            throw new Error(
                "plantCrop failed too many times, check chat log to see what happened"
            );
        }
        return;
    }

    // Find all land blocks within a maximum distance of 32
    const blocks = bot.findBlocks({
        matching: block => block && lands.includes(block.name),
        maxDistance: 32,
        count: 1000
    });

    // For each block in the filtered list, move to the block, equip the seeds, and plant them
    let planted = 0;
    for (const position of blocks) {
        for (const direction of directions) {
            const blockOffset = bot.blockAt(position.add(direction));
            if (blockOffset.name === 'air') {
                await bot.pathfinder.goto(new GoalNear(position.x, position.y, position.z, 3));
                await bot.equip(seeds, 'hand');
                await bot.activateBlock(bot.blockAt(position));
                planted++;
            }
        }
    }
    if (planted > 0) {
        bot.chat(`All available land has been planted with ${crop}.`);
    }
}

async function plantSweetBerryBushes(bot) {
    await plantCrop(bot, "sweet_berries", ["farmland", "dirt"], [new Vec3(0, 1, 0)]);
}

async function plantWheatSeeds(bot) {
    await plantCrop(bot, "wheat_seeds", ["farmland"], [new Vec3(0, 1, 0)]);
}

async function plantPotatoes(bot) {
    await plantCrop(bot, "potato", ["farmland"], [new Vec3(0, 1, 0)]);
}

async function plantCarrots(bot) {
    await plantCrop(bot, "carrot", ["farmland"], [new Vec3(0, 1, 0)]);
}

async function plantBeetrootSeeds(bot) {
    await plantCrop(bot, "beetroot_seeds", ["farmland"], [new Vec3(0, 1, 0)]);
}

async function plantCocoaBeans(bot) {
    await plantCrop(bot, "cocoa_beans", ["jungle_log"], [new Vec3(1, 0, 0), new Vec3(-1, 0, 0), new Vec3(0, 0, 1), new Vec3(0, 0, -1)]);
}

async function plantMelonSeeds(bot) {
    await plantCrop(bot, "melon_seeds", ["farmland"], [new Vec3(0, 1, 0)]);
}

async function plantPumpkinSeeds(bot) {
    await plantCrop(bot, "pumpkin_seeds", ["farmland"], [new Vec3(0, 1, 0)]);
}

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
        bot.chat(`No ${crop} nearby`);
        _farmFailCount++;
        if (_farmFailCount > 10) {
            throw new Error(
                "harvest failed too many times, check chat log to see what happened"
            );
        }
        return;
    }
    bot.chat(`Harvesting ${crop}`);

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

    bot.chat(`Harvested ${crops.length} ${crop}`);
}

async function harvestBerries(bot, pos) {
    await harvest(bot, pos, "sweet_berry_bush", true, true, block => block.getProperties().age > 1);
}

async function harvestWheat(bot, pos) {
    await harvest(bot, pos, "wheat", true, false, block => block.getProperties().age > 6);
}

async function harvestPotatoes(bot, pos) {
    await harvest(bot, pos, "potatoes", true, false, block => block.getProperties().age > 6);
}

async function harvestCarrots(bot, pos) {
    await harvest(bot, pos, "carrots", true, false, block => block.getProperties().age > 6);
}

async function harvestBeetroot(bot, pos) {
    await harvest(bot, pos, "beetroots", true, false, block => block.getProperties().age > 2);
}

async function harvestCocoa(bot, pos) {
    await harvest(bot, pos, "cocoa", false, false, block => block.getProperties().age > 1);
}

async function harvestMelons(bot, pos) {
    await harvest(bot, pos, "melon", false, false);
}

async function harvestPumpkins(bot, pos) {
    await harvest(bot, pos, "pumpkin", false, false);
}

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
    bot.chat(`Milked cow`);
    }
}

async function destroyCrop(bot, crop) {
    const blockByName = mcData.blocksByName[crop];
    if (!blockByName) {
        throw new Error(`No block named ${crop}`);
    }
    const blocks = bot.findBlocks({
      matching: [blockByName.id],
      maxDistance: 32,
      count: 1000
    });
    if (blocks.length === 0) {
      return;
    }
    bot.chat(`Destroying all ${crop} nearby`);

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