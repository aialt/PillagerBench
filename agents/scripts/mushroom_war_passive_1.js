async function winGame(bot) {
  const teamCenter = new Vec3($team_center);
  const teamName = "$team_name";
  const slimeCount = 8;

  async function removeSlimeBlocks() {
    if (!await blockExists(bot, "slime_block", teamCenter, 7)) {
      return;
    }
    bot.chat(`Removing slime blocks in the ${teamName} area`);
    await mineBlock(bot, "slime_block", slimeCount, teamCenter, 7);
  }
  while (true) {
    await bot.waitForTicks(20);
    await removeSlimeBlocks();
  }
}

await winGame(bot);
