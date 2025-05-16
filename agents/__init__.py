import importlib.resources
from abc import ABCMeta
from pathlib import Path

from bench.agent import Agent

agent_classes = {}
agent_files = importlib.resources.files("agents")

for agent_file in agent_files.iterdir():  # type: Path
    if agent_file.name.endswith(".py") and agent_file.name != "__init__.py":
        agent_module = importlib.import_module(f"agents.{agent_file.stem}")
        for key in agent_module.__dict__:
            cls = agent_module.__dict__[key]
            if isinstance(cls, ABCMeta) and issubclass(cls, Agent) and "name" in cls.__dict__:
                name = agent_module.__dict__[key].__dict__["name"]
                agent_classes[name] = agent_module.__dict__[key]

__all__ = ["agent_classes"]
