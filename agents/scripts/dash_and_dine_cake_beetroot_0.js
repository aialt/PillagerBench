async function winGame(bot) {
  const eggPos = new Vec3(-7, -60, 5);
  const bucketPos = new Vec3(-7, -60, -7);
  const wheatPos = new Vec3(-19, -60, -1);
  const serverName = "$server_name";

  async function grabEggs(bot, pos) {
    await getItemFromChest(bot, pos, {"egg": 16});
  }

  async function grabBuckets(bot, pos) {
    await getItemFromChest(bot, pos, {"bucket": 16});
  }

  // Craft cakes to win the game
  await grabEggs(bot, eggPos);
  await grabBuckets(bot, bucketPos);
  while (true) {
    await bot.waitForTicks(20);
    for (let i = 0; i < 15; i++) {
      let buckets = bot.inventory.findInventoryItem(mcData.itemsByName.bucket.id);
      if (!buckets) {
        break;
      }
      await milkCow(bot);
    }
    for (let i = 0; i < 5; i++) {
      await bot.waitForTicks(20);
      await harvestSugarCane(bot, -61);
      await harvestWheat(bot, wheatPos);
      await plantWheatSeeds(bot);
      await craftItem(bot, "sugar", 2);
      await craftItem(bot, "cake", 1);
    }
    await giveToPlayer(bot, "cake", serverName, -1);
    await grabEggs(bot, eggPos);
  }
}

await winGame(bot);
