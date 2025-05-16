import json
import os
import re
from pathlib import Path

import yaml
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import scipy.stats as stats
from collections import defaultdict


blue_team_normal_rewards = {
    "do_nothing": 0.0,
    "aggressive": 20.27,
    "balanced": 16.75,
    "passive": 25.23,
    "slimy": 22.18,
    "berries": 34.73,
    "cake_beetroot": 7.83,
    "melon_pumpkin": 15.82,
    "potato_cookie": 13.12,
}


def read_scenario_yaml(scenario_yaml_path):
    with open(scenario_yaml_path, 'r') as file:
        data = yaml.safe_load(file)
    scenario_name = data.get('name')
    team_red_agent = data.get('agent')
    opponents = data.get('opponents', [])
    if not opponents:
        raise ValueError(f"No opponents found in {scenario_yaml_path}")
    team_blue_agent = opponents[0]

    # Shorten names starting with 'mushroom_war_'
    prefixes = ['mushroom_war_', 'dash_and_dine_']
    for prefix in prefixes:
        if team_red_agent.startswith(prefix):
            team_red_agent = team_red_agent.replace(prefix, '')
        if team_blue_agent.startswith(prefix):
            team_blue_agent = team_blue_agent.replace(prefix, '')

    actual_team_blue_agent = team_blue_agent
    prev_episodes = 0

    if 'agent_kwargs' in data:
        agent_kwargs = data['agent_kwargs']
        if 'checkpoint_path' in agent_kwargs:
            checkpoint = Path(agent_kwargs['checkpoint_path'][7:])
            assert checkpoint.exists(), f"Checkpoint not found: {checkpoint}"
            prev_scenario_name, prev_team_red_agent, prev_team_blue_agent, _, _ = read_scenario_yaml(checkpoint.parents[1] / 'scenario.yaml')
            assert prev_scenario_name == scenario_name, f"Scenario name mismatch: {prev_scenario_name} != {scenario_name}"
            assert prev_team_red_agent == team_red_agent, f"Red team agent mismatch: {prev_team_red_agent} != {team_red_agent}"
            prev_episodes = int(checkpoint.parent.stem.replace('episode', '')) + 1
            if prev_team_blue_agent == team_blue_agent:
                team_blue_agent = "same opponent " + scenario_name
            else:
                team_blue_agent = "different opponent " + scenario_name

    return scenario_name, team_red_agent, team_blue_agent, actual_team_blue_agent, prev_episodes

def read_rewards(reward_file_path, points_scale=1.0):
    with open(reward_file_path, 'r') as file:
        return [float(line.strip()) * points_scale for line in file]

def collect_data(logs_dirs, ignore_agents, ignore_scenarios, points_scale_dict):
    ignore_agents = set(ignore_agents or [])
    ignore_scenarios = set(ignore_scenarios or [])
    rewards_r = defaultdict(list)
    rewards_b = defaultdict(list)
    blue_teams = defaultdict(list)
    reward_diffs = defaultdict(list)
    winrates = defaultdict(list)
    red_rewards_by_second = defaultdict(list)
    reward_diffs_by_episode = defaultdict(list)
    rewards_r_by_episode = defaultdict(list)
    rewards_b_by_episode = defaultdict(list)
    rollout_num_iters = defaultdict(list)
    ai_invoke_times = []
    ai_input_tokens = []
    ai_output_tokens = []
    dedupe_ratios = []

    ai_invoke_pattern = re.compile(
        r"AI invoke: response time: (\d+\.\d+)s, usage metadata: \{'input_tokens': (\d+), 'output_tokens': (\d+),")

    for suffix, logs_dir in logs_dirs:
        main_log_path = os.path.join(logs_dir, '..', 'main.log')
        if os.path.isfile(main_log_path):
            with open(main_log_path, 'r', encoding="UTF-8") as log_file:
                initial_length = None
                for line in log_file:
                    if "Initial length of events for" in line:
                        parts = line.split(":")
                        length = int(parts[-1].strip())
                        initial_length = length
                    elif "Final length of events for" in line:
                        parts = line.split(":")
                        length = int(parts[-1].strip())
                        if initial_length and initial_length > 0:
                            dedupe_ratios.append(length / initial_length)
                    elif "AI invoke: response time" in line:
                        match = ai_invoke_pattern.search(line)
                        if match:
                            ai_invoke_times.append(float(match.group(1)))
                            ai_input_tokens.append(int(match.group(2)))
                            ai_output_tokens.append(int(match.group(3)))

        for scenario_name in os.listdir(logs_dir):
            scenario_path = os.path.join(logs_dir, scenario_name)
            if not os.path.isdir(scenario_path):
                continue
            scenario_yaml_path = os.path.join(scenario_path, 'scenario.yaml')
            if not os.path.isfile(scenario_yaml_path):
                print(f"scenario.yaml not found in {scenario_path}, skipping.")
                continue
            try:
                scenario_name, team_red_agent, team_blue_agent, actual_team_blue_agent, prev_episodes = read_scenario_yaml(scenario_yaml_path)
            except Exception as e:
                print(f"Error reading {scenario_yaml_path}: {e}")
                continue

            team_red_agent += suffix

            if scenario_name in ignore_scenarios:
                continue

            points_scale = points_scale_dict.get(scenario_name, 1.0)

            if team_red_agent in ignore_agents or team_blue_agent in ignore_agents:
                continue

            for episode_name in os.listdir(scenario_path):
                episode_path = os.path.join(scenario_path, episode_name)
                if not os.path.isdir(episode_path) or not episode_name.startswith('episode'):
                    continue
                episode_index = int(episode_name.replace('episode', '')) + prev_episodes
                rewards_path = os.path.join(episode_path, 'rewards')
                if not os.path.isdir(rewards_path):
                    continue
                red_team_file = os.path.join(rewards_path, 'red_team.txt')
                blue_team_file = os.path.join(rewards_path, 'blue_team.txt')
                if not os.path.isfile(red_team_file) or not os.path.isfile(blue_team_file):
                    continue
                red_team_code_file = os.path.join(episode_path, "red_team", 'code.json')
                if os.path.isfile(red_team_code_file):
                    with open(red_team_code_file, 'r') as file:
                        red_team_code = json.load(file)
                    for agent, inner in red_team_code.items():
                        if "info" in inner and "rollout_num_iter" in inner["info"]:
                            rollout_num_iters[episode_index].append(inner["info"]["rollout_num_iter"])
                try:
                    red_rewards = read_rewards(red_team_file, points_scale)
                    blue_rewards = read_rewards(blue_team_file, points_scale)

                    if len(red_rewards) < 121 or len(blue_rewards) < 121:
                        print(f"Insufficient rewards in {episode_path}, skipping.")
                        continue

                    rewards_r[(team_red_agent, team_blue_agent)].append(red_rewards[120])
                    rewards_b[(team_red_agent, team_blue_agent)].append(blue_rewards[120])
                    blue_teams[(team_red_agent, team_blue_agent)].append(actual_team_blue_agent)
                    diff = red_rewards[120] - blue_rewards[120]
                    reward_diffs[(team_red_agent, team_blue_agent)].append(diff)

                    if diff > 0:
                        winrates[(team_red_agent, team_blue_agent)].append(1)
                    elif diff < 0:
                        winrates[(team_red_agent, team_blue_agent)].append(0)
                    else:
                        winrates[(team_red_agent, team_blue_agent)].append(0.5)

                    # Collect rewards at each second for the line graph
                    for second, reward in enumerate(red_rewards[:121]):
                        red_rewards_by_second[(team_red_agent, second)].append(reward)

                    # Collect rewards for each episode
                    # reward_diffs_by_episode[(scenario_name, episode_index)].append(diff)
                    reward_diffs_by_episode[(team_red_agent, episode_index)].append(diff)
                    rewards_r_by_episode[(team_red_agent, episode_index)].append(red_rewards[120])
                    rewards_b_by_episode[(team_red_agent, episode_index)].append(blue_rewards[120])

                except Exception as e:
                    print(f"Error reading rewards in {rewards_path}: {e}")
                    continue

    return {
        "rewards_r": rewards_r,
        "rewards_b": rewards_b,
        "blue_teams": blue_teams,
        "reward_diffs": reward_diffs,
        "winrates": winrates,
        "red_rewards_by_second": red_rewards_by_second,
        "reward_diffs_by_episode": reward_diffs_by_episode,
        "rewards_r_by_episode": rewards_r_by_episode,
        "rewards_b_by_episode": rewards_b_by_episode,
        "rollout_num_iters": rollout_num_iters,
        "ai_invoke_times": ai_invoke_times,
        "ai_input_tokens": ai_input_tokens,
        "ai_output_tokens": ai_output_tokens,
        "dedupe_ratios": dedupe_ratios,
    }

def plot_heatmaps2(rewards_r, rewards_b, reward_diffs, winrates):
    red_agents = sorted(set([agents[0] for agents in reward_diffs.keys()]))
    blue_agents = sorted(set([agents[1] for agents in reward_diffs.keys()]))

    # Put do_nothing as the first agent
    if 'do_nothing' in red_agents:
        red_agents.remove('do_nothing')
        red_agents.insert(0, 'do_nothing')
    if 'do_nothing' in blue_agents:
        blue_agents.remove('do_nothing')
        blue_agents.insert(0, 'do_nothing')

    avg_rewards_r = pd.DataFrame(index=red_agents, columns=blue_agents)
    sabotage = pd.DataFrame(index=red_agents, columns=blue_agents)
    avg_diffs = pd.DataFrame(index=red_agents, columns=blue_agents)
    std_diffs = pd.DataFrame(index=red_agents, columns=blue_agents)
    avg_winrates = pd.DataFrame(index=red_agents, columns=blue_agents)

    for (red, blue), scores in rewards_r.items():
        avg_rewards_r.loc[red, blue] = np.mean(rewards_r.get((red, blue), []))
    for (red, blue), scores in rewards_b.items():
        sabotage.loc[red, blue] = blue_team_normal_rewards[blue] - np.mean(rewards_b.get((red, blue), []))
    for (red, blue), scores in reward_diffs.items():
        avg_diffs.loc[red, blue] = np.mean(reward_diffs.get((red, blue), []))
        std_diffs.loc[red, blue] = np.std(reward_diffs.get((red, blue), []))
    for (red, blue), scores in winrates.items():
        avg_winrates.loc[red, blue] = np.mean(winrates.get((red, blue), []))

    avg_rewards_r = avg_rewards_r.astype(float)
    sabotage = sabotage.astype(float)
    avg_diffs = avg_diffs.astype(float)
    std_diffs = std_diffs.astype(float)
    avg_winrates = avg_winrates.astype(float)

    # Add average column
    rewards_avg = {red: np.concatenate([np.array(rewards_r.get((red, blue), [])) for blue in blue_agents]) for red in red_agents}
    reward_diffs_avg = {red: np.concatenate([np.array(reward_diffs.get((red, blue), [])) for blue in blue_agents]) for red in red_agents}
    winrates_avg = {red: np.concatenate([np.array(winrates.get((red, blue), [])) for blue in blue_agents]) for red in red_agents}
    avg_rewards_r['all opponents'] = [np.mean(rewards_avg[red]) for red in red_agents]
    sabotage['all opponents'] = [np.mean([sabotage.loc[red, blue] for blue in blue_agents]) for red in red_agents]
    avg_diffs['all opponents'] = [np.mean(reward_diffs_avg[red]) for red in red_agents]
    std_diffs['all opponents'] = [np.std(reward_diffs_avg[red]) for red in red_agents]
    avg_winrates['all opponents'] = [np.mean(winrates_avg[red]) for red in red_agents]

    # Plot average reward heatmap
    # plt.figure(figsize=(12, 6))
    plt.imshow(avg_rewards_r, interpolation='nearest', cmap='viridis')
    plt.title('Average Reward (Red Team)')
    plt.colorbar(label='Average Reward')
    plt.xticks(range(len(avg_rewards_r.columns)), avg_rewards_r.columns, rotation=45)
    plt.yticks(range(len(red_agents)), red_agents)

    for i in range(len(red_agents)):
        for j in range(len(avg_diffs.columns)):
            value = avg_rewards_r.iloc[i, j]
            if not pd.isna(value):
                plt.text(j, i, f"{value:.2f}", ha='center', va='center',
                         color='white' if value < 0 else 'black')

    plt.tight_layout()
    plt.show()

    # Plot average sabotage heatmap
    # plt.figure(figsize=(12, 6))
    plt.imshow(sabotage, interpolation='nearest', cmap='viridis')
    plt.title('Average Sabotage (Red Team)')
    plt.colorbar(label='Average Sabotage')
    plt.xticks(range(len(sabotage.columns)), sabotage.columns, rotation=45)
    plt.yticks(range(len(red_agents)), red_agents)

    for i in range(len(red_agents)):
        for j in range(len(avg_diffs.columns)):
            value = sabotage.iloc[i, j]
            if not pd.isna(value):
                plt.text(j, i, f"{value:.2f}", ha='center', va='center',
                         color='white' if value < 0 else 'black')

    plt.tight_layout()
    plt.show()

    # Plot average reward difference heatmap
    # plt.figure(figsize=(12, 6))
    plt.imshow(avg_diffs, interpolation='nearest', cmap='viridis')
    plt.title('Average Reward Difference (Red - Blue)')
    plt.colorbar(label='Average Reward Difference')
    plt.xticks(range(len(avg_diffs.columns)), avg_diffs.columns, rotation=45)
    plt.yticks(range(len(red_agents)), red_agents)

    for i in range(len(red_agents)):
        for j in range(len(avg_diffs.columns)):
            value = avg_diffs.iloc[i, j]
            std = std_diffs.iloc[i, j]
            if not pd.isna(value):
                plt.text(j, i, f"{value:.2f}", ha='center', va='center',
                         color='white' if value < 0 else 'black')

    plt.tight_layout()
    plt.show()

    # Plot winrate heatmap
    # plt.figure(figsize=(12, 6))
    plt.imshow(avg_winrates, interpolation='nearest', cmap='coolwarm')
    plt.title('Winrate (Red Team)')
    plt.colorbar(label='Winrate')
    plt.xticks(range(len(avg_winrates.columns)), avg_winrates.columns, rotation=45)
    plt.yticks(range(len(red_agents)), red_agents)

    for i in range(len(red_agents)):
        for j in range(len(avg_winrates.columns)):
            value = avg_winrates.iloc[i, j]
            if not pd.isna(value):
                plt.text(j, i, f"{value:.2f}", ha='center', va='center',
                         color='white' if abs(value - 0.5) > 0.25 else 'black')

    plt.tight_layout()
    plt.show()

def plot_heatmaps(rewards_r, rewards_b, blue_teams, reward_diffs, winrates):
    red_agents = sorted(set([agents[0] for agents in reward_diffs.keys()]))
    blue_agents = sorted(set([agents[1] for agents in reward_diffs.keys()]))

    # Put do_nothing as the first agent
    if 'do_nothing' in red_agents:
        red_agents.remove('do_nothing')
        red_agents.insert(0, 'do_nothing')
    if 'do_nothing' in blue_agents:
        blue_agents.remove('do_nothing')
        blue_agents.insert(0, 'do_nothing')

    # Sort red and blue agents to the same order as the keys of blue normal rewards
    red_agents = sorted(red_agents, key=lambda x: list(blue_team_normal_rewards.keys()).index(x) if x in blue_team_normal_rewards else -1)
    blue_agents = sorted(blue_agents, key=lambda x: list(blue_team_normal_rewards.keys()).index(x) if x in blue_team_normal_rewards else -1)

    if 'random' in red_agents:
        red_agents.remove('random')
        red_agents.insert(0, 'random')

    avg_rewards_r = pd.DataFrame(index=red_agents, columns=blue_agents)
    sabotage = pd.DataFrame(index=red_agents, columns=blue_agents)
    avg_diffs = pd.DataFrame(index=red_agents, columns=blue_agents)
    avg_winrates = pd.DataFrame(index=red_agents, columns=blue_agents)

    for (red, blue), scores in rewards_r.items():
        avg_rewards_r.loc[red, blue] = np.mean(rewards_r.get((red, blue), []))
    for (red, blue), scores in rewards_b.items():
        sabotage.loc[red, blue] = np.mean([blue_team_normal_rewards.get(b, 0) for b in blue_teams.get((red, blue), [])]) - np.mean(rewards_b.get((red, blue), []))
    for (red, blue), scores in reward_diffs.items():
        avg_diffs.loc[red, blue] = np.mean(reward_diffs.get((red, blue), []))
    for (red, blue), scores in winrates.items():
        avg_winrates.loc[red, blue] = np.mean(winrates.get((red, blue), []))

    avg_rewards_r = avg_rewards_r.astype(float)
    sabotage = sabotage.astype(float)
    avg_diffs = avg_diffs.astype(float)
    avg_winrates = avg_winrates.astype(float)

    # Add average column
    rewards_avg = {red: np.concatenate([np.array(rewards_r.get((red, blue), [])) for blue in blue_agents]) for red in red_agents}
    reward_diffs_avg = {red: np.concatenate([np.array(reward_diffs.get((red, blue), [])) for blue in blue_agents]) for red in red_agents}
    winrates_avg = {red: np.concatenate([np.array(winrates.get((red, blue), [])) for blue in blue_agents]) for red in red_agents}
    avg_rewards_r['all opponents'] = [np.mean(rewards_avg[red]) for red in red_agents]
    sabotage['all opponents'] = [np.mean([sabotage.loc[red, blue] for blue in blue_agents]) for red in red_agents]
    avg_diffs['all opponents'] = [np.mean(reward_diffs_avg[red]) for red in red_agents]
    avg_winrates['all opponents'] = [np.mean(winrates_avg[red]) for red in red_agents]

    fig, axes = plt.subplots(1, 3, figsize=(30, 6))

    # Plot average reward heatmap
    im1 = axes[0].imshow(avg_rewards_r, interpolation='nearest', cmap='viridis')
    axes[0].set_title('Points (Red Team)')
    fig.colorbar(im1, ax=axes[0], label='Points')
    axes[0].set_xticks(range(len(avg_rewards_r.columns)))
    axes[0].set_xticklabels(avg_rewards_r.columns, rotation=45)
    axes[0].set_yticks(range(len(red_agents)))
    axes[0].set_yticklabels(red_agents)
    for i in range(len(red_agents)):
        for j in range(len(avg_rewards_r.columns)):
            value = avg_rewards_r.iloc[i, j]
            if not pd.isna(value):
                axes[0].text(j, i, f"{value:.2f}", ha='center', va='center', color='white' if value < 0 else 'black')

    # Plot average sabotage heatmap
    im2 = axes[1].imshow(sabotage, interpolation='nearest', cmap='viridis')
    axes[1].set_title('Sabotage (Red Team)')
    fig.colorbar(im2, ax=axes[1], label='Sabotage')
    axes[1].set_xticks(range(len(sabotage.columns)))
    axes[1].set_xticklabels(sabotage.columns, rotation=45)
    axes[1].set_yticks(range(len(red_agents)))
    axes[1].set_yticklabels(red_agents)
    for i in range(len(red_agents)):
        for j in range(len(sabotage.columns)):
            value = sabotage.iloc[i, j]
            if not pd.isna(value):
                axes[1].text(j, i, f"{value:.2f}", ha='center', va='center', color='white' if value < 0 else 'black')

    # Plot winrate heatmap
    im3 = axes[2].imshow(avg_winrates, interpolation='nearest', cmap='coolwarm')
    axes[2].set_title('Win rate (Red Team)')
    fig.colorbar(im3, ax=axes[2], label='Win rate')
    axes[2].set_xticks(range(len(avg_winrates.columns)))
    axes[2].set_xticklabels(avg_winrates.columns, rotation=45)
    axes[2].set_yticks(range(len(red_agents)))
    axes[2].set_yticklabels(red_agents)
    for i in range(len(red_agents)):
        for j in range(len(avg_winrates.columns)):
            value = avg_winrates.iloc[i, j]
            if not pd.isna(value):
                axes[2].text(j, i, f"{value:.2f}", ha='center', va='center', color='white' if abs(value - 0.5) > 0.25 else 'black')

    plt.tight_layout()
    plt.show()

    # Plot average reward difference heatmap
    # plt.figure(figsize=(12, 6))
    plt.imshow(avg_diffs, interpolation='nearest', cmap='viridis')
    plt.title('Points Difference (Red - Blue)')
    plt.colorbar(label='Points Difference')
    plt.xticks(range(len(avg_diffs.columns)), avg_diffs.columns, rotation=45)
    plt.yticks(range(len(red_agents)), red_agents)

    for i in range(len(red_agents)):
        for j in range(len(avg_diffs.columns)):
            value = avg_diffs.iloc[i, j]
            if not pd.isna(value):
                plt.text(j, i, f"{value:.2f}", ha='center', va='center',
                         color='white' if value < 0 else 'black')

    plt.tight_layout()
    plt.show()

def plot_reward_progression(rewards_over_time: dict[(str, int), list[float]]):
    red_agents = sorted(set(agent for agent, _ in rewards_over_time.keys()))
    seconds = range(121)
    confidence_level = 0.95
    z_value = stats.norm.ppf((1 + confidence_level) / 2)

    plt.figure(figsize=(10, 6))
    for agent in red_agents:
        avg_rewards = np.array([np.mean(rewards_over_time.get((agent, second), [0])) for second in seconds])
        std_rewards = np.array([np.std(rewards_over_time.get((agent, second), [0])) for second in seconds])
        sample_sizes = np.array([len(rewards_over_time.get((agent, second), [0])) for second in seconds])
        margin_of_error = z_value * (std_rewards / np.sqrt(sample_sizes))
        lower_bound = avg_rewards - margin_of_error
        upper_bound = avg_rewards + margin_of_error
        plt.fill_between(seconds, lower_bound, upper_bound, alpha=0.2)
        plt.plot(seconds, avg_rewards, label=agent)

    plt.title('Points Over Time (Red Team)')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Points')
    plt.legend(title='Red Team Agents')
    plt.grid()
    plt.show()

def plot_rewards_by_episode(*rewards_by_episode: dict[(str, int), list[float]]):
    red_agents = sorted(set(agent for agent, _ in rewards_by_episode[0].keys()))
    episodes = sorted(set(episode for _, episode in rewards_by_episode[0].keys()))
    confidence_level = 0.95
    z_value = stats.norm.ppf((1 + confidence_level) / 2)

    plt.figure(figsize=(10, 6))
    labels = ["Red Team", "Blue Team"]
    colours = ['red', 'blue']
    for i in range(len(rewards_by_episode)):
        for agent in red_agents:
            avg_rewards = np.array([np.mean(rewards_by_episode[i].get((agent, episode), [0])) for episode in episodes])
            std_rewards = np.array([np.std(rewards_by_episode[i].get((agent, episode), [0])) for episode in episodes])
            sample_sizes = np.array([len(rewards_by_episode[i].get((agent, episode), [0])) for episode in episodes])
            margin_of_error = z_value * (std_rewards / np.sqrt(sample_sizes))
            lower_bound = avg_rewards - margin_of_error
            upper_bound = avg_rewards + margin_of_error
            # plt.fill_between(episodes, lower_bound, upper_bound, alpha=0.2)
            plt.xticks(episodes, [str(episode) for episode in episodes])
            # plt.plot(episodes, avg_rewards, label=labels[i], marker='^', color=colours[i])
            plt.plot(episodes, avg_rewards, label=agent, marker='^')

    # plt.title('TactiCrafter Points Difference over Episodes of Self-play (Red - Blue)')
    plt.title('Points Difference over Episode (Red - Blue)')
    plt.xlabel('Episode')
    plt.ylabel('Points Difference')
    plt.legend(title='Scenario')
    plt.grid()
    plt.show()

def plot_blue_normal_rewards():
    # Create the bar chart
    plt.figure(figsize=(7.5, 4.5))  # Adjust figure size for better readability
    plt.bar(blue_team_normal_rewards.keys(), blue_team_normal_rewards.values())  # Use a pleasant color

    # Add labels and title
    plt.xlabel('Built-in Opponent (Blue Team)', fontsize=12)
    plt.ylabel('Points', fontsize=12)
    plt.title('Average Points Achieved by Blue Team Against Do-Nothing Red Team', fontsize=14)

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')

    # Add gridlines for easier comparison
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Add value labels on top of the bars for better clarity
    for i, point in enumerate(blue_team_normal_rewards.values()):
        plt.text(i, point + 0.5, f'{point:.2f}', ha='center', va='bottom', fontsize=12)

    # Adjust layout to prevent labels from overlapping
    plt.ylim(0, 38)  # <--- ADD THIS LINE
    plt.tight_layout()

    # Display the plot
    plt.show()

def main():
    logs_dirs = [
        # ("", 'results/debug/test_mushroom_war_baselines/2025-01-10/21-15-45/logs'),
        # ("", 'results/debug/test_mushroom_war_baselines/2025-01-08/14-46-49/logs'),
        # ("", 'results/debug/test_dash_and_dine_baselines/2025-01-24/12-45-58/logs'),
        # ("", 'results/debug/tacticrafter_vs_berries2/logs'),
        # ("", 'results/debug/tacticrafter_vs_berries/logs'),
        # ("", 'results/debug/tacticrafter_dash_and_dine/logs'),
        # ("", 'results/debug/tacticrafter_mushroom_war/logs'),
        # ("-GPT-4o", 'results/test_gpt4o/14-26-41/logs'),
        # ("-GPT-4o", 'results/test_gpt4o/19-39-43/logs'),
        # ("-o3-mini-medium", 'results/test_o3-mini/16-15-23/logs'),
        # ("-gemini-2.0-flash", 'results/test_gemini/11-28-15/logs'),
        # ("-gemini-2.0-flash", 'results/test_gemini/17-47-58/logs'),
        ("", 'results/test_gpt4o/14-26-41/logs'),
        ("", 'results/test_gpt4o/19-39-43/logs'),
        # ("_no_causal", 'results/ablation_no_causal/14-39-25/logs'),
        # ("_no_opponent", 'results/ablation_no_opp/09-31-49/logs'),
        # ("", 'results/test_adaptation/15-06-27/logs'),
        # ("", 'results/test_adaptation/15-24-48/logs'),
        # ("", 'results/test_self_play/15-25-21/logs'),
        # ("", 'results/test_self_play_improvement/21-34-47/logs'),
        ("", 'results/test_random/14-18-03/logs'),
        ("", 'results/test_cot/00-00-37/logs'),
    ]
    ignore_agents = []
    # ignore_agents = ['do_nothing']  # Add agent names to ignore
    ignore_scenarios = []
    # ignore_scenarios = ["Mushroom War"]
    # ignore_scenarios = ["Dash and Dine"]
    points_scale = {
        "Mushroom War": 1,
        "Dash and Dine": 0.1,
    }
    plot = True

    for _, logs_dir in logs_dirs:
        if not os.path.isdir(logs_dir):
            print(f"Logs directory '{logs_dir}' not found.")
            return

    print("Collecting data...")
    data = collect_data(logs_dirs, ignore_agents, ignore_scenarios, points_scale)
    if not data['reward_diffs']:
        print("No data collected.")
        return

    if plot:
        print("Plotting heatmaps...")
        plot_heatmaps(data['rewards_r'], data['rewards_b'], data['blue_teams'], data['reward_diffs'], data['winrates'])

        print("Plotting reward progression...")
        plot_reward_progression(data['red_rewards_by_second'])

        print("Plotting rewards by episode...")
        plot_rewards_by_episode(data['reward_diffs_by_episode'])
        # plot_rewards_by_episode(data['rewards_r_by_episode'], data['rewards_b_by_episode'])
        # plot_blue_normal_rewards()

    for (red, blue), scores_b in data['rewards_b'].items():
        if red == 'do_nothing':
            print(f"{red} vs {blue}: blue = {np.mean(scores_b):.2f}")

    print(f"Average rollout_num_iters: {np.mean([iters for episode_iters in data['rollout_num_iters'].values() for iters in episode_iters]):.2f}")
    for episode, iters in data['rollout_num_iters'].items():
        print(f"Episode {episode}: {np.mean(iters):.2f}")

    print(f"Average AI invoke time: {np.mean(data['ai_invoke_times']):.2f}s")
    print(f"Average AI input tokens: {np.mean(data['ai_input_tokens']):.2f}")
    print(f"Average AI output tokens: {np.mean(data['ai_output_tokens']):.2f}")
    print(f"Total AI input tokens: {np.sum(data['ai_input_tokens'])}")
    print(f"Total AI output tokens: {np.sum(data['ai_output_tokens'])}")
    print(f"Average dedupe ratio: {np.mean(data['dedupe_ratios']):.2f}")
    print(f"Average output tokens per second: {np.sum(data['ai_output_tokens']) / np.sum(data['ai_invoke_times']):.2f}")

if __name__ == "__main__":
    main()
