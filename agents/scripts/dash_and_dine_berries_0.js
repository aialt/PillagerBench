async function winGame(bot) {
  const berryPos = new Vec3(-11, -60, 6);
  const serverName = "$server_name";

  while (true) {
    await harvestBerries(bot, berryPos);
    await plantSweetBerryBushes(bot);
    await bot.waitForTicks(20);
    await giveToPlayer(bot, "sweet_berries", serverName, -1);
  }
}

await winGame(bot);
