async function winGame(bot) {
  const wheatPos = new Vec3(-19, -60, -1);
  const cocoaPos = new Vec3(-15, -60, -8);
  const serverName = "$server_name";

  // Harvest wheat and cocoa and craft cookies
  await harvestWheat(bot, wheatPos);
  await plantWheatSeeds(bot);
  await destroyCrop(bot, "carrots");
  await plantWheatSeeds(bot);
  while (true) {
    await harvestWheat(bot, wheatPos);
    await plantWheatSeeds(bot);
    await bot.waitForTicks(20);
    await harvestCocoa(bot, cocoaPos);
    await plantCocoaBeans(bot);
    await craftItem(bot, "cookie", 8);
    await giveToPlayer(bot, "cookie", serverName, -1);
  }
}

await winGame(bot);
