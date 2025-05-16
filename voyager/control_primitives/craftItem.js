function failedCraftFeedback(bot, name, item, craftingTable) {
    const recipes = bot.recipesAll(item.id, null, craftingTable);
    if (!recipes.length) {
        throw new Error(`No crafting table nearby`);
    } else {
        const recipes = bot.recipesAll(
            item.id,
            null,
            mcData.blocksByName.crafting_table.id
        );
        // find the recipe with the fewest missing ingredients
        var min = 999;
        var min_recipe = null;
        for (const recipe of recipes) {
            const delta = recipe.delta;
            var missing = 0;
            for (const delta_item of delta) {
                if (delta_item.count < 0) {
                    const inventory_item = bot.inventory.findInventoryItem(
                        mcData.items[delta_item.id].name,
                        null
                    );
                    if (!inventory_item) {
                        missing += -delta_item.count;
                    } else {
                        missing += Math.max(
                            -delta_item.count - inventory_item.count,
                            0
                        );
                    }
                }
            }
            if (missing < min) {
                min = missing;
                min_recipe = recipe;
            }
        }
        const delta = min_recipe.delta;
        let message = "";
        for (const delta_item of delta) {
            if (delta_item.count < 0) {
                const inventory_item = bot.inventory.findInventoryItem(
                    mcData.items[delta_item.id].name,
                    null
                );
                if (!inventory_item) {
                    message += ` ${-delta_item.count} more ${
                        mcData.items[delta_item.id].name
                    }, `;
                } else {
                    if (inventory_item.count < -delta_item.count) {
                        message += ` ${
                            -delta_item.count - inventory_item.count
                        } more ${mcData.items[delta_item.id].name}`;
                    }
                }
            }
        }
        bot.chat(`I cannot make ${name} because I need: ${message}`);
    }
}

async function craftItem(bot, name, count = 1) {
    // return if name is not string
    if (typeof name !== "string") {
        throw new Error("name for craftItem must be a string");
    }
    // return if count is not number
    if (typeof count !== "number") {
        throw new Error("count for craftItem must be a number");
    }
    const itemByName = mcData.itemsByName[name];
    if (!itemByName) {
        throw new Error(`No item named ${name}`);
    }
    const craftingTable = bot.findBlock({
        matching: mcData.blocksByName.crafting_table.id,
        maxDistance: 32,
    });
    if (!craftingTable) {
        bot.chat("Craft without a crafting table");
    } else {
        await bot.pathfinder.goto(
            new GoalLookAtBlock(craftingTable.position, bot.world)
        );
    }
    const recipe = bot.recipesFor(itemByName.id, null, 1, craftingTable)[0];
    if (recipe) {
        bot.chat(`I can make ${name}`);
        try {
            await bot.craft(recipe, count, craftingTable);
            bot.chat(`I did the recipe for ${name} ${count} times`);
        } catch (err) {
            bot.chat(`I cannot do the recipe for ${name} ${count} times`);
        }
    } else {
        failedCraftFeedback(bot, name, itemByName, craftingTable);
        _craftItemFailCount++;
        if (_craftItemFailCount > 10) {
            throw new Error(
                "craftItem failed too many times, check chat log to see what happened"
            );
        }
    }
}
