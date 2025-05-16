async function winGame(bot) {
  const pumpkinPos = new Vec3(-16, -60, -1);
  const eggPos = new Vec3(-7, -60, 5);
  const serverName = "$server_name";

  // Harvest pumpkins and craft pumpkin pies
  while (true) {
    await getItemFromChest(bot, eggPos, {"egg": 16});
    await bot.waitForTicks(20);
    await harvestSugarCane(bot, -61);
    await harvestPumpkins(bot, pumpkinPos);
    await craftItem(bot, "sugar", 3);
    await craftItem(bot, "pumpkin_pie", 3);
    await giveToPlayer(bot, "pumpkin_pie", serverName, -1);
  }
}

await winGame(bot);
