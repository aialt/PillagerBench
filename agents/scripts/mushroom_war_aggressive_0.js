async function winGame(bot) {
  const teamCenter = new Vec3($team_center);
  const teamName = "$team_name";
  const opponentCenter = new Vec3($opponent_center);
  const opponentName = "$opponent_name";
  const sabotageSlimeCount = 8; // Number of slime blocks to place in the red team area

  async function removeSlimeBlocks() {
    if (!await blockExists(bot, "slime_block", teamCenter, 7)) {
      return;
    }
    bot.chat(`Removing slime blocks in the ${teamName} area`);
    await mineBlock(bot, "slime_block", sabotageSlimeCount, teamCenter, 7);
  }
  async function placeSlimeBlocks() {
    bot.chat(`Placing slime blocks in the ${opponentName} area`);
    for (let i = 0; i < sabotageSlimeCount; i++) {
      const randomOffset = new Vec3(Math.floor(Math.random() * 8) - 4, 0, Math.floor(Math.random() * 8) - 4);
      const placePosition = opponentCenter.plus(randomOffset);
      await placeItem(bot, "slime_block", placePosition);
    }
  }
  while (true) {
    await bot.waitForTicks(20);
    await removeSlimeBlocks();
    await placeSlimeBlocks();
  }
}

await winGame(bot);
