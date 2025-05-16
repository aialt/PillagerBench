async function winGame(bot) {
  const potatoPos = new Vec3(-19, -60, 5);
  const furnacePos = new Vec3(2, -59, -1);
  const hoePos = new Vec3(-11, -59, -1);
  const serverName = "$server_name";

  async function bakePotatoes(){
    let item = bot.inventory.items().find(item => item.name === "potato");
    if (!item) {
        return;
    }
    await bot.pathfinder.goto(new GoalNear(furnacePos, 3), true);
    await smeltItem(bot, "potato", "coal", 8);
  }

  // Harvest potatoes and cook them into baked potatoes
  await getItemFromChest(bot, hoePos, {"netherite_hoe": 1});
  await harvestPotatoes(bot, potatoPos);
  await plantPotatoes(bot);
  await destroyCrop(bot, "sweet_berry_bush");
  await tillLand(bot);
  while (true) {
    await harvestPotatoes(bot, potatoPos);
    await plantPotatoes(bot);
    await bot.waitForTicks(20);
    await bakePotatoes();
    await giveToPlayer(bot, "baked_potato", serverName, -1);
    await giveToPlayer(bot, "potato", serverName, -1);
  }
}

await winGame(bot);
