from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectPaths:
    root: Path

    @property
    def env_info(self) -> Path:
        return self.root / "env_info.json"

    @property
    def registry(self) -> Path:
        return self.root / "experiment_registry.json"

    @property
    def context(self) -> Path:
        return self.root / "project_context.json"

    @property
    def concept(self) -> Path:
        return self.root / "concept.json"

    @property
    def plan(self) -> Path:
        return self.root / "experiment_plan.yaml"

    @property
    def next_plan(self) -> Path:
        return self.root / "next_plan.yaml"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def config(self) -> Path:
        return self.root / "config.yaml"
