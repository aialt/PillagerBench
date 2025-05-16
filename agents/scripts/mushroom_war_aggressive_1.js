async function winGame(bot) {
  const teamCenter = new Vec3($team_center);
  const teamName = "$team_name";
  const teamCollectableBlockName = "$team_collectable_block_name";
  const opponentCenter = new Vec3($opponent_center);
  const opponentName = "$opponent_name";
  const opponentCollectableBlockName = "$opponent_collectable_block_name";

  async function removeSlimeBlocks() {
    if (!await blockExists(bot, "slime_block", teamCenter, 7)) {
      return;
    }
    bot.chat(`Removing slime blocks in the ${teamName} area`);
    await mineBlock(bot, "slime_block", 8, teamCenter, 7);
  }
  async function harvest() {
    if (!await blockExists(bot, teamCollectableBlockName, teamCenter, 7)) {
      await removeSlimeBlocks();
      return;
    }
    bot.chat(`Harvesting ${teamCollectableBlockName} in the ${teamName} area`);
    await mineBlock(bot, teamCollectableBlockName, 15, teamCenter, 7);
  }
  async function sabotageOpponent() {
    if (!await blockExists(bot, opponentCollectableBlockName, opponentCenter, 7)) {
      return;
    }
    bot.chat(`Destroying ${opponentCollectableBlockName} in the ${opponentName} area.`);
    await mineBlock(bot, opponentCollectableBlockName, 15, opponentCenter, 7);
  }
  while (true) {
    await bot.waitForTicks(20);
    await harvest();
    await sabotageOpponent();
  }
}

await winGame(bot);
