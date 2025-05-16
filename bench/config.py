from dataclasses import dataclass, MISSING
from typing import Optional

from hydra.core.config_store import ConfigStore


@dataclass
class ScenarioConfig:
    name: str = MISSING
    agent: str = MISSING
    opponents: list[str] = MISSING
    kwargs: dict = MISSING
    num_episodes: int = 1
    agent_kwargs: Optional[dict] = None


@dataclass
class Config:
    scenarios: list[ScenarioConfig] = MISSING
    agents: dict[str, dict] = MISSING
    mc_port: int = 49172
    server_port: int = 3000
    env_wait_ticks: int = 80


cs = ConfigStore.instance()
cs.store(name="config", node=Config)
cs.store(group="scenario", name="scenario", node=ScenarioConfig)
