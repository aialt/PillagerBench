async function mineBlock(bot, name, count = 1, point = null, maxDistance = 32) {
    // return if name is not string
    if (typeof name !== "string") {
        throw new Error(`name for mineBlock must be a string`);
    }
    if (typeof count !== "number") {
        throw new Error(`count for mineBlock must be a number`);
    }
    const blockByName = mcData.blocksByName[name];
    if (!blockByName) {
        throw new Error(`No block named ${name}`);
    }
    const blocks = bot.findBlocks({
        point: point,
        matching: [blockByName.id],
        maxDistance: maxDistance,
        count: count,
    });
    if (blocks.length === 0) {
        bot.chat(`No ${name} nearby, please explore first`);
        _mineBlockFailCount++;
        if (_mineBlockFailCount > 10) {
            throw new Error(
                "mineBlock failed too many times, make sure you explore before calling mineBlock"
            );
        }
        return;
    }
    const targets = [];
    for (let i = 0; i < blocks.length; i++) {
        const target = bot.blockAt(blocks[i]);
        targets.push(target);
        // bot.chat(`Found ${name} at ${target.position}`);
    }
    await bot.collectBlock.collect(targets, {
        ignoreNoPath: true,
        count: count,
    });
    bot.chat(`Mined ${blocks.length} ${name}`);
    bot.save(`${name}_mined`);
}

async function blockExists(bot, name, point, maxDistance = 32) {
    // return if name is not string
    if (typeof name !== "string") {
        throw new Error(`name for mineBlock must be a string`);
    }
    const blockByName = mcData.blocksByName[name];
    if (!blockByName) {
        throw new Error(`No block named ${name}`);
    }
    const blocks = bot.findBlocks({
        point: point,
        matching: [blockByName.id],
        maxDistance: maxDistance,
        count: 1,
    });
    return blocks.length > 0;
}