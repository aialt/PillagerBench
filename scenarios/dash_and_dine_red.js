bot.chat("starting dining scenario...");

const rewards = {
    apple: 6.4,
    baked_potato: 11,
    beetroot: 2.2,
    beetroot_soup: 13.2,
    bread: 11,
    cake: 16.8,
    carrot: 6.6,
    chorus_fruit: 6.4,
    cooked_beef: 20.8,
    cooked_chicken: 13.2,
    cooked_cod: 11,
    cooked_mutton: 15.6,
    cooked_porkchop: 20.8,
    cooked_rabbit: 11,
    cooked_salmon: 15.6,
    cookie: 2.4,
    dried_kelp: 1.6,
    enchanted_golden_apple: 13.6,
    golden_apple: 13.6,
    glow_berries: 2.4,
    golden_carrot: 20.4,
    honey_bottle: 7.2,
    melon_slice: 3.2,
    mushroom_stew: 13.2,
    poisonous_potato: 3.2,
    potato: 1.6,
    pufferfish: 1.2,
    pumpkin_pie: 12.8,
    rabbit_stew: 22,
    raw_beef: 4.8,
    raw_chicken: 3.2,
    raw_cod: 2.4,
    raw_mutton: 3.2,
    raw_porkchop: 4.8,
    raw_rabbit: 4.8,
    raw_salmon: 2.4,
    rotten_flesh: 4.8,
    spider_eye: 5.2,
    suspicious_stew: 13.2,
    suspicious_stew_saturation: 34.2,
    sweet_berries: 2.4,
    tropical_fish: 1.2,
};

// Set team items empty. Its a list of string
const team_items = [];
const max_items = 3;

async function runDiningScenario(bot) {
    // On pick-up, check if in rewards list, update team_items, increment score
    const items = bot.inventory.items();
    let rewardCount = 0;

    items.forEach((item) => {
        if (item.name in rewards) {
            if (!(team_items.includes(item.name)) && team_items.length < max_items){
                team_items.push(item.name);
                bot.chat(`Locked-in ${item.name} as a submission item for team_red`);
            }

            if (team_items.includes(item.name)) {
                rewardCount += item.count * rewards[item.name];
            }
        }
    });

    // Update scoreboard
    if (rewardCount > 0) {
        bot.chat(`/scoreboard players add red_team Scores ${Math.round(rewardCount)}`);
        bot.chat(`Scored ${Math.round(rewardCount)} points for team_red`);
    }

    // Clear inventory
    if (items.length > 0) {
        await bot.creative.clearInventory()
    }
    await bot.waitForTicks(40)
}

while (true) {
    await runDiningScenario(bot);
}