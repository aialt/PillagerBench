import importlib.resources
from abc import ABCMeta
from pathlib import Path

from bench.scenario import Scenario

scenario_classes = {}
scenario_files = importlib.resources.files("scenarios")

for scenario_file in scenario_files.iterdir():  # type: Path
    if scenario_file.name.endswith(".py") and scenario_file.name != "__init__.py":
        scenario_module = importlib.import_module(f"scenarios.{scenario_file.stem}")
        for key in scenario_module.__dict__:
            cls = scenario_module.__dict__[key]
            if isinstance(cls, ABCMeta) and issubclass(cls, Scenario) and "name" in cls.__dict__:
                name = scenario_module.__dict__[key].__dict__["name"]
                scenario_classes[name] = scenario_module.__dict__[key]

__all__ = ["scenario_classes"]
