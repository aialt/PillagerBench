from .json_utils import *


def spawn_commands(usernames, spawn_locations):
    commands = []
    for name, pos in spawn_locations.items():
        if name not in usernames:
            raise ValueError(f"Spawn location for {name} not found in scenario")
        commands.append(f"bot.chat('/tp {name} {pos['x']} {pos['y']} {pos['z']}');")
    return ''.join(commands)


def spawn_commands_2(usernames: list[list[str]], spawn_locations: list[list[tuple[int, int, int]]]):
    commands = []
    for i, team in enumerate(spawn_locations):
        for j, pos in enumerate(team):
            name = usernames[i][j]
            commands.append(f"bot.chat('/tp {name} {pos[0]} {pos[1]} {pos[2]}');")
    return ''.join(commands)


def gamemode_commands(usernames: list[list[str]], gamemode):
    commands = []
    for team in usernames:
        for name in team:
            commands.append(f"bot.chat('/gamemode {gamemode} {name}');")
    return ''.join(commands)


def scores_teams_commands(usernames: list[list[str]], team_names: list[str], team_colors: list[str]):
    commands = [
        "bot.chat('/scoreboard objectives add Scores dummy');",
        "bot.chat('/scoreboard objectives setdisplay sidebar Scores');"
    ]
    for i, team in enumerate(usernames):
        team_name = team_names[i]
        team_color = team_colors[i]
        commands.append(f"bot.chat('/scoreboard players set {team_name} Scores 0');")
        commands.append(f"bot.chat('/team add {team_name}');")
        commands.append(f"bot.chat('/team modify {team_name} color {team_color}');")
        commands.append(f"bot.chat('/team join {team_name} {team_name}');")
        for name in team:
            commands.append(f"bot.chat('/team join {team_name} {name}');")
    return ''.join(commands)


def add_block_commands(block_positions):
    blocks = []
    positions = []
    facing = None

    for block_type, pos_list in block_positions.items():
        if block_type == 'facing':
            facing = pos_list
            continue

        blocks.extend([block_type] * len(pos_list))
        positions.extend(pos_list)

    return f"await replaceMinedBlock(bot, {json_dumps(blocks)}, {json_dumps(positions)}, '{facing}');"


def chest_commands(block_positions, chest_contents):
    if 'chest' not in block_positions:
        print('Warning: No chest found in scenario')
        return ""

    chest_pos = block_positions['chest'][0]
    return f"bot.chat('/data merge block {chest_pos['x']} {chest_pos['y']} {chest_pos['z']}  {chest_contents}');"


def remove_drops_commands():
    return "bot.chat('/kill @e[type=item]');"


def remove_blocks_commands(block_types, center_position):
    # x, y, z = center_position['x'], center_position['y'], center_position['z']
    # commands = []
    # for block_type in block_types:
    #     commands.append(f"bot.chat('/fill {str(x-16)} {str(y-16)} {str(z-16)} {str(x+16)} {str(y+16)} {str(z+16)} air replace {block_type}');")
    # return ''.join(commands)
    return f"await clearBlocks(bot, {json_dumps(block_types)}, {json_dumps(center_position)});"


def skins_commands(url):
    return f"bot.chat('/skin set URL classic {url}');"


def parse_chest_contents(chest_contents):
    if not isinstance(chest_contents, dict):
        raise ('Chest contents must be a dictionary')

    items = []
    i = 0
    for item, count in chest_contents.items():
        items.append(f"{{Slot:{i}b,id:\"minecraft:{item}\",Count:{count}b}}")
        i += 1

    return f"{{Items:[{','.join(items)}]}}"
