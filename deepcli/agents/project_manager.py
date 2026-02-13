from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from deepcli.core.io import read_json, write_json
from deepcli.core.models import ProjectPaths


class ProjectManager:
    def __init__(self, project_dir: Path):
        self.paths = ProjectPaths(project_dir.resolve())

    def read_json(self, path: Path, default: Any = None) -> Any:
        return read_json(path, default)

    def write_json(self, path: Path, data: Any) -> None:
        write_json(path, data)

    def bootstrap_context(self, env_info: dict, experiment_count: int) -> dict:
        context = {
            "project_root": str(self.paths.root),
            "initialized_at": datetime.now().isoformat(),
            "env_info": env_info,
            "experiment_count": experiment_count,
        }
        write_json(self.paths.context, context)
        return context
