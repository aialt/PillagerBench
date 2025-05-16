// Moves to the player with username and drops them the specified item. Use num=-1 to drop the maximum count.
async function giveToPlayer(bot, itemType, username, num=-1) {
    let player = bot.players[username].entity
    await goToPlayer(bot, username);
    await bot.lookAt(player.position);
    await bot.waitForTicks(5);
    await discard(bot, itemType, num);
    return true;
}