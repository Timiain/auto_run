from __future__ import annotations

from datetime import datetime

from deepcli.core.io import read_json


class IterativeOptimizer:
    def __init__(self, pm, planner):
        self.pm = pm
        self.planner = planner

    def iterate(self, run_id: str, concept: dict):
        previous = read_json(self.pm.paths.results / run_id / "metrics.json", {})
        budget = concept.get("budget", {}) if isinstance(concept.get("budget", {}), dict) else {}
        epochs = int(budget.get("epochs", 8))
        success = previous.get("status") == "SUCCESS"
        budget["epochs"] = epochs + (5 if success else 2)
        concept = {**concept, "budget": budget, "prev_status": previous.get("status")}
        next_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_iter"
        return self.planner.create_plan(concept, run_id=next_id, output=self.pm.paths.next_plan, last_metrics=previous)
