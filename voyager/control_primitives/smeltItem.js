async function smeltItem(bot, itemName, fuelName, count = 1) {
    // return if itemName or fuelName is not string
    if (typeof itemName !== "string" || typeof fuelName !== "string") {
        throw new Error("itemName or fuelName for smeltItem must be a string");
    }
    // return if count is not a number
    if (typeof count !== "number") {
        throw new Error("count for smeltItem must be a number");
    }
    const item = mcData.itemsByName[itemName];
    const fuel = mcData.itemsByName[fuelName];
    if (!item) {
        throw new Error(`No item named ${itemName}`);
    }
    if (!fuel) {
        throw new Error(`No item named ${fuelName}`);
    }
    const item2 = bot.inventory.findInventoryItem(item.id, null);
    if (!item2) {
        bot.chat(`No ${itemName} to smelt in inventory`);
        return;
    }
    count = Math.min(count, item2.count);
    const furnaceBlocks = bot.findBlocks({
        matching: mcData.blocksByName.furnace.id,
        maxDistance: 32,
        count: 100,
    });
    if (!furnaceBlocks || furnaceBlocks.length === 0) {
        bot.chat(`No furnace nearby`);
        return;
    }
    let furnace = null;
    for (let i = 0; i < furnaceBlocks.length; i++) {
        const furnaceBlockPos = furnaceBlocks[i];
        const furnaceBlock = bot.blockAt(furnaceBlockPos);
        if (!furnaceBlock) {
            continue;
        }
        await bot.pathfinder.goto(
            new GoalLookAtBlock(furnaceBlock.position, bot.world)
        );
        try {
            furnace = await bot.openFurnace(furnaceBlock);
            if (furnace.inputItem() || furnace.outputItem()) {
                // This furnace is in use
                furnace.close();
                furnace = null;
                continue;
            }
            break;
        }
        catch (error) {
            _smeltItemFailCount++;
            if (_smeltItemFailCount > 10) {
                throw error;
            }
        }
    }
    if (!furnace) {
        bot.chat(`No available furnace`);
        return;
    }
    bot.chat(`Smelting ${count} ${itemName} with ${fuelName}`);
    let success_count = 0;
    for (let i = 0; i < count; i++) {
        if (!bot.inventory.findInventoryItem(item.id, null)) {
            bot.chat(`No ${itemName} to smelt in inventory`);
            break;
        }
        if (furnace.fuelSeconds < 15 && furnace.fuelItem()?.name !== fuelName) {
            if (!bot.inventory.findInventoryItem(fuel.id, null)) {
                bot.chat(`No ${fuelName} as fuel in inventory`);
                break;
            }
            await furnace.putFuel(fuel.id, null, 1);
            await bot.waitForTicks(20);
            if (!furnace.fuel && furnace.fuelItem()?.name !== fuelName) {
                throw new Error(`${fuelName} is not a valid fuel`);
            }
        }
        await furnace.putInput(item.id, null, 1);
        await bot.waitForTicks(12 * 20);
        if (!furnace.outputItem()) {
            throw new Error(`${itemName} is not a valid input`);
        }
        await furnace.takeOutput();
        success_count++;
    }
    furnace.close();
    if (success_count > 0) bot.chat(`Smelted ${success_count} ${itemName}.`);
    else {
        bot.chat(
            `Failed to smelt ${itemName}, please check the fuel and input.`
        );
        _smeltItemFailCount++;
        if (_smeltItemFailCount > 10) {
            throw new Error(
                `smeltItem failed too many times, please check the fuel and input.`
            );
        }
    }
}
