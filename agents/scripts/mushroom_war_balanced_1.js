async function sabotageOpponent(bot) {
  const opponentCenter = new Vec3($opponent_center);
  const opponentName = "$opponent_name";
  const opponentCollectableBlockName = "$opponent_collectable_block_name";

  while (true) {
    await bot.waitForTicks(20);
    // Destroy red mushroom blocks in the red team area
    if (await blockExists(bot, opponentCollectableBlockName, opponentCenter, 7)) {
        bot.chat(`Destroying ${opponentCollectableBlockName} in the ${opponentName} area.`);
        await mineBlock(bot, opponentCollectableBlockName, 15, opponentCenter, 7);
    }
    // Repeat the sabotage cycle
  }
}

await sabotageOpponent(bot);
