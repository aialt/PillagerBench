async function giveToPlayer(bot, itemType, username, num=-1) {
    let player = bot.players[username].entity
    if (!player){
        throw new Error(`Could not find ${username}.`);
    }
    let item = bot.inventory.items().find(item => item.name === itemType);
    if (!item) {
        bot.chat(`I do not have any ${itemType} to give.`);
        return;
    }
    await goToPlayer(bot, username);
    await bot.lookAt(player.position);
    await bot.waitForTicks(5);
    let discarded = await discard(bot, itemType, num);
    bot.chat(`Gave ${discarded} ${itemType} to ${username}`);
    return true;
}

async function goToPlayer(bot, username, distance=2) {
    let player = bot.players[username].entity
    if (!player) {
        throw new Error(`Could not find ${username}.`);
    }

    // const move = new pf.Movements(bot);
    // bot.pathfinder.setMovements(move);
    await bot.pathfinder.goto(new GoalFollow(player, distance), true);
}

async function discard(bot, itemName, num=-1) {
    let discarded = 0;
    while (true) {
        let item = bot.inventory.items().find(item => item.name === itemName);
        if (!item) {
            break;
        }
        let to_discard = num === -1 ? item.count : Math.min(num - discarded, item.count);
        await bot.toss(item.type, null, to_discard);
        discarded += to_discard;
        if (num !== -1 && discarded >= num) {
            break;
        }
    }
    return discarded;
}