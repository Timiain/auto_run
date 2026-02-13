from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from deepcli.core.io import read_yaml


class DataRecorder:
    def __init__(self, pm):
        self.pm = pm

    def init_run_dir(self, run_id: str) -> Path:
        run_dir = self.pm.paths.results / run_id
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_metrics(self, run_dir: Path, metrics: dict):
        (run_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


class ExperimentRunner:
    def __init__(self, pm):
        self.pm = pm
        self.recorder = DataRecorder(pm)

    @staticmethod
    def _params_to_argv(params: dict) -> list[str]:
        args = []
        for k, v in params.items():
            args.extend([f"--{k}", str(v)])
        return args

    def run(self, plan_file: str | None = None):
        pfile = Path(plan_file) if plan_file else self.pm.paths.plan
        plan = read_yaml(pfile)
        run_id = plan["plan_id"]
        run_dir = self.recorder.init_run_dir(run_id)
        (run_dir / "config.yaml").write_text(pfile.read_text(encoding="utf-8"), encoding="utf-8")
        log_path = run_dir / "logs" / "run.log"

        metrics = {"run_id": run_id, "status": "SUCCESS", "steps": []}
        with log_path.open("w", encoding="utf-8") as f:
            for step in plan.get("steps", []):
                script = self.pm.paths.root / step["script"]
                if not script.exists():
                    metrics["status"] = "FAILED"
                    metrics["steps"].append({"name": step["name"], "status": "FAILED", "reason": "script not found"})
                    continue

                cmd = [sys.executable, str(script)] + self._params_to_argv(step.get("params", {}))
                f.write(f"\n$ {' '.join(cmd)}\n")
                proc = subprocess.run(cmd, cwd=self.pm.paths.root, capture_output=True, text=True, check=False)
                f.write(proc.stdout)
                f.write(proc.stderr)
                status = "SUCCESS" if proc.returncode == 0 else "FAILED"
                metrics["steps"].append({"name": step["name"], "status": status, "returncode": proc.returncode})
                if proc.returncode != 0:
                    metrics["status"] = "FAILED"

        self.recorder.write_metrics(run_dir, metrics)
        return metrics
