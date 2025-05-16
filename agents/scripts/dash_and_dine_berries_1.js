async function winGame(bot) {
  const berryPos = new Vec3(-19, -60, -7);
  const serverName = "$server_name";
  const crops = ["potatoes", "beetroots"];
  const cropItems = {
    "beetroots": "beetroot",
    "wheat": "wheat",
    "carrots": "carrot",
    "potatoes": "potato",
  }

  async function replaceCropsWithBerries() {
    for (let i = 0; i < crops.length; i++) {
      const crop = crops[i];
      await destroyCrop(bot, crop);
      await harvestBerries(bot, berryPos);
      await plantSweetBerryBushes(bot);
      await bot.waitForTicks(20);
      await giveToPlayer(bot, cropItems[crop], serverName, -1);
      await bot.waitForTicks(20);
    }
  }

  await replaceCropsWithBerries();
  while (true) {
    await harvestBerries(bot, berryPos);
    await plantSweetBerryBushes(bot);
    await bot.waitForTicks(20);
    await giveToPlayer(bot, "sweet_berries", serverName, -1);
  }
}

await winGame(bot);
