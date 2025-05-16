async function winGame(bot) {
  const bowlPos = new Vec3(-3, -59, -1);
  const beetrootPos = new Vec3(-15, -60, 6);
  const serverName = "$server_name";

  async function grabBowls(bot, pos) {
    await getItemFromChest(bot, pos, {"bowl": 64});
  }

  async function destroyMelonPumpkins(bot) {
    const melonPumpkins = bot.findBlocks({
      matching: block => block.name.includes("melon_stem") || block.name.includes("pumpkin_stem"),
      maxDistance: 32,
      count: 20
    });
    if (melonPumpkins.length === 0) {
      return;
    }
    bot.chat(`Destroying melon and pumpkin stems`);

    const targets = [];
    for (let i = 0; i < melonPumpkins.length; i++) {
        const target = bot.blockAt(melonPumpkins[i]);
        targets.push(target);
    }
    await bot.collectBlock.collect(targets, {
      ignoreNoPath: true,
      count: targets.length,
      goalNear: true,
      activateBlock: false,
    });

    bot.chat(`Destroyed ${melonPumpkins.length} melons and pumpkin stems`);
  }

  // Craft cakes to win the game
  await grabBowls(bot, bowlPos);
  await harvestBeetroot(bot, beetrootPos);
  await plantBeetrootSeeds(bot);
  await destroyMelonPumpkins(bot);
  await plantBeetrootSeeds(bot);
  while (true) {
    await harvestBeetroot(bot, beetrootPos);
    await plantBeetrootSeeds(bot);
    await bot.waitForTicks(20);
    let item = bot.inventory.items().find(item => item.name === "beetroot");
    if (item && item.count >= 6) {
      await craftItem(bot, "beetroot_soup", 1);
      await giveToPlayer(bot, "beetroot_soup", serverName, -1);
    }
  }
}

await winGame(bot);
