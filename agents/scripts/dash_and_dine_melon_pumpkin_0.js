async function winGame(bot) {
  const melonPos = new Vec3(-16, -60, -1);
  const serverName = "$server_name";

  // Harvest melons
  while (true) {
    await harvestMelons(bot, melonPos);
    await bot.waitForTicks(20);
    await giveToPlayer(bot, "melon_slice", serverName, -1);
  }
}

await winGame(bot);
