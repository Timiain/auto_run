from __future__ import annotations

import shutil
import subprocess
from typing import Any

from deepcli.core.io import write_json


class EnvInstaller:
    def __init__(self, pm):
        self.pm = pm

    def setup(self, force: bool = False) -> dict[str, Any]:
        req = self.pm.paths.root / "requirements.txt"
        env_name = f"{self.pm.paths.root.name}_env"
        conda = shutil.which("conda")

        info: dict[str, Any] = {
            "name": env_name,
            "conda_path": None,
            "packages": [],
            "requirements_file": str(req) if req.exists() else None,
            "status": "SKIPPED",
        }
        if req.exists():
            info["packages"] = [line.strip() for line in req.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]

        if conda and req.exists():
            if force:
                subprocess.run([conda, "env", "remove", "-y", "-n", env_name], check=False, capture_output=True, text=True)
            proc = subprocess.run([conda, "create", "-y", "-n", env_name, "--file", str(req)], check=False, capture_output=True, text=True)
            info["status"] = "READY" if proc.returncode == 0 else "FAILED"
            if proc.returncode != 0:
                info["error"] = proc.stderr[-2000:]
        elif not conda:
            info["status"] = "CONDA_NOT_FOUND"

        write_json(self.pm.paths.env_info, info)
        return info
