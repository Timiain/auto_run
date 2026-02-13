from __future__ import annotations

from datetime import datetime

from deepcli.core.io import read_json, write_yaml
from deepcli.llm.client import get_chat_response


class ExperimentPlanner:
    def __init__(self, pm):
        self.pm = pm

    def _smart_budget(self, concept: dict, last_metrics: dict | None = None) -> dict:
        budget = concept.get("budget", {}) if isinstance(concept.get("budget", {}), dict) else {}
        if "epochs" not in budget:
            budget["epochs"] = 10
        if last_metrics and last_metrics.get("status") == "FAILED":
            budget["epochs"] = max(3, int(budget["epochs"]) // 2)
        return budget

    @staticmethod
    def _filter_params(raw_params: dict, allowed_params: list[str]) -> dict:
        if not allowed_params:
            return raw_params
        return {k: v for k, v in raw_params.items() if k in allowed_params}

    def _llm_hint(self, concept: dict) -> str | None:
        cfg = read_json(self.pm.paths.root / ".deepcli_llm.json", {})
        if not cfg.get("enabled"):
            return None
        messages = [
            {"role": "system", "content": "You are an ML experiment planning assistant. Return concise tuning hints."},
            {"role": "user", "content": f"idea={concept.get('idea','')}, target={concept.get('target_metric','accuracy')}"},
        ]
        return get_chat_response(
            api_key=cfg.get("api_key", ""),
            base_url=cfg.get("base_url", ""),
            model=cfg.get("model", "ollama#llama3.1"),
            messages=messages,
            temperature=0.2,
        )

    def create_plan(self, concept: dict, run_id: str | None = None, output=None, last_metrics: dict | None = None):
        registry = read_json(self.pm.paths.registry, [])
        run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        budget = self._smart_budget(concept, last_metrics)
        llm_hint = self._llm_hint(concept)

        steps = []
        env_name = read_json(self.pm.paths.env_info, {}).get("name")
        for rec in registry:
            if rec.get("type") != "python":
                continue
            default_params = {"idea": concept.get("idea", "baseline"), **budget}
            if "eval" in rec.get("name", "").lower() and "batch_size" not in default_params:
                default_params["batch_size"] = 32
            params = self._filter_params(default_params, rec.get("cli_args", []))

            steps.append(
                {
                    "name": rec["name"],
                    "script": rec["path"],
                    "params": params,
                    "env": env_name,
                }
            )

        plan = {
            "plan_id": run_id,
            "objective": concept.get("target_metric", "accuracy"),
            "llm_hint": llm_hint,
            "steps": steps,
        }
        write_yaml(output or self.pm.paths.plan, plan)
        return plan
