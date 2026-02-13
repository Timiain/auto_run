from __future__ import annotations

import json
from pathlib import Path

from deepcli.core.io import read_json


class Reporter:
    def __init__(self, pm):
        self.pm = pm

    def generate(self, run_id: str, output_file: str | None = None) -> Path:
        run_dir = self.pm.paths.results / run_id
        metrics = read_json(run_dir / "metrics.json", {})
        cfg = (run_dir / "config.yaml").read_text(encoding="utf-8") if (run_dir / "config.yaml").exists() else ""
        log_file = run_dir / "logs" / "run.log"
        log_tail = ""
        if log_file.exists():
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            log_tail = "\n".join(lines[-80:])

        report = f"# Report: {run_id}\n\n"
        report += f"## Status\n\n- Overall: **{metrics.get('status','UNKNOWN')}**\n\n"
        report += "## Metrics\n\n```json\n" + json.dumps(metrics, ensure_ascii=False, indent=2) + "\n```\n\n"
        report += "## Plan\n\n```yaml\n" + cfg + "\n```\n\n"
        report += "## Log tail\n\n```text\n" + log_tail + "\n```\n"

        self.pm.paths.reports.mkdir(parents=True, exist_ok=True)
        out = Path(output_file) if output_file else self.pm.paths.reports / f"{run_id}.md"
        out.write_text(report, encoding="utf-8")
        return out
