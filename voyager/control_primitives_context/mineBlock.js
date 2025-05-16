// Mine 3 cobblestone: mineBlock(bot, "stone", 3);
async function mineBlock(bot, name, count = 1, point = null, maxDistance = 32) {
    const blocks = bot.findBlocks({
        point: point,
        matching: (block) => {
            return block.name === name;
        },
        maxDistance: maxDistance,
        count: count,
    });
    const targets = [];
    for (let i = 0; i < Math.min(blocks.length, count); i++) {
        targets.push(bot.blockAt(blocks[i]));
    }
    await bot.collectBlock.collect(targets, { ignoreNoPath: true });
}
