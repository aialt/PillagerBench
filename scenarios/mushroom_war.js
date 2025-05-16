const fs = require('fs');

bot.chat("starting cleanup scenario...");

const waste_cutoff = 7;
const reward_respawn_rate = 0.1;
const waste_respawn_rate = 0.02;
const dirty_tick_speed = 0;
const clean_tick_speed = 100;

const stem_block = mcData.blocksByName.mushroom_stem;
const waste_block = mcData.blocksByName.slime_block;

const team_centers = [
    new Vec3(-9, -60, -10),
    new Vec3(-9, -60, 6),
];
const reward_blocks = [
    mcData.blocksByName.red_mushroom_block,
    mcData.blocksByName.brown_mushroom_block,
];

const n_teams = team_centers.length;
const team_area_radius = 7;

// Set the tick speed to high to grow berries
// bot.chat(`/gamerule randomTickSpeed 40000`);
// await bot.waitForTicks(60);
// bot.chat(`/gamerule randomTickSpeed ${dirty_tick_speed}`);

// Find the waste and reward blocks
const wasteLocations = bot.findBlocks({
    matching: waste_block.id,
    maxDistance: 32,
    count: 100
});
const stemLocations = bot.findBlocks({
    matching: stem_block.id,
    maxDistance: 32,
    count: 100
});

// Get the reward block locations for each team separately
const rewardLocations = team_centers.map((center, index) => {
    return bot.findBlocks({
        point: center,
        matching: reward_blocks[index].id,
        maxDistance: team_area_radius,
        count: 100
    });
});

// Set clean is false for each team. Its a list of booleans
var clean = new Array(n_teams).fill(false)

async function runCleanupScenario(bot) {
    for (let i = 0; i < n_teams; i++) {
        // Check if there are less than cutoff waste blocks
        if (bot.findBlocks({
            point: team_centers[i],
            matching: waste_block.id,
            maxDistance: team_area_radius,
            count: 100
        }).length <= waste_cutoff) {

            if (!clean[i]) {
                // Set the tick speed to high to grow berries
                bot.chat(`Team ${i} is clean!`);
                // bot.chat(`/gamerule randomTickSpeed ${clean_tick_speed}`);
                clean[i] = true;
            }

            // Respawn the reward blocks using /setblock
            rewardLocations[i].forEach(location => {
                const { x, y, z } = location;

                // Check if the block is missing at this location
                const currentBlock = bot.blockAt(location);
                if (currentBlock && currentBlock.name !== reward_blocks[i].name) {

                    // Generate a random number between 0 and 1
                    const rand = Math.random();

                    // Respawn the block with probability
                    if (rand < reward_respawn_rate) {
                        bot.chat(`/setblock ${x} ${y} ${z} ${reward_blocks[i].name}`);
                    }
                }
            });
        }
        else {
            if (clean[i]) {
                // Set the tick speed to low to stop berries
                bot.chat(`Team ${i} is too dirty!`);
                // bot.chat(`/gamerule randomTickSpeed ${dirty_tick_speed}`);
                clean[i] = false;
            }
        }
    }

    // Respawn the waste blocks using /setblock
    wasteLocations.forEach(location => {
        const { x, y, z } = location;

        // Generate a random number between 0 and 1
        const rand = Math.random();

        // Respawn the block with probability
        if (rand < waste_respawn_rate) {
            bot.chat(`/setblock ${x} ${y} ${z} slime_block`);
        }
    });
    // stemLocations.forEach(location => {
    //     const { x, y, z } = location;

    //     // Generate a random number between 0 and 1
    //     const rand = Math.random();

    //     // Respawn the block with probability
    //     if (rand < reward_respawn_rate) {
    //         bot.chat(`/setblock ${x} ${y} ${z} mushroom_stem`);
    //     }
    // });

    await bot.waitForTicks(20);
}

while (true) {
    await runCleanupScenario(bot);
}