#!/usr/bin/env python3
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except Exception:  # pragma: no cover
    class _YamlCompat:
        @staticmethod
        def safe_dump(data, allow_unicode=True, sort_keys=False):
            return json.dumps(data, ensure_ascii=not allow_unicode, indent=2)

        @staticmethod
        def safe_load(text):
            if text is None:
                return None
            text = text.strip()
            if not text:
                return None
            return json.loads(text)

    yaml = _YamlCompat()

try:
    import tiktoken
except Exception:  # pragma: no cover
    tiktoken = None

try:
    import openai
except Exception:  # pragma: no cover
    openai = None

try:
    from ollama import Client as OllClient
except Exception:  # pragma: no cover
    OllClient = None


openai_client = None
ollama_client = None


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Simple placeholder pricing model for local accounting."""
    return 0.0


def save_token_result(tag: str, model: str, tokens_in: int, tokens_out: int, messages: List[dict], answer: str) -> str:
    logs = Path("token_logs")
    logs.mkdir(exist_ok=True)
    path = logs / f"{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(
        json.dumps(
            {
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "messages": messages,
                "answer": answer,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(path)


def get_chat_response(api_key, base_url, model, messages, stream=False, temperature=0.7, num_ctx=24000, num_predict=4096):
    global openai_client, ollama_client

    system_prompt = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
    prompt = "".join([m["content"] for m in messages if m["role"] == "user"])

    if "ollama" in model:
        parts = re.split('#', model)
        print("parts[1]={}".format(parts[1]))

        if ollama_client is None:
            if OllClient is None:
                raise RuntimeError("ollama package is not installed")
            ollama_client = OllClient(host=base_url, headers={'x-some-header': 'some-value'})
        response = ollama_client.chat(model=parts[1], messages=messages, options={"temperature": temperature, "num_ctx": num_ctx, "num_predict": num_predict})

        if response:
            answer = response.message.content
        else:
            return None

    else:
        print("Using openai interface api")
        if openai_client is None:
            if openai is None:
                raise RuntimeError("openai package is not installed")
            openai_client = openai.OpenAI(api_key=api_key, base_url=base_url)
        print("api_key:{} base_url:{}".format(api_key, base_url))
        response = None
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream,
                temperature=temperature
            )
        except Exception as e:
            print(f"Failed to generate chat response. Error type: {type(e).__name__}")
            print(f"Error details: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"HTTP Status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            return None

        if response:
            answer = response.choices[0].message.content
        else:
            return None

    try:
        if tiktoken is None:
            raise RuntimeError("tiktoken missing")
        if model in ["o1-preview", "o1-mini", "claude-3.5-sonnet", "o1"]:
            encoding = tiktoken.encoding_for_model("gpt-4o")
        elif model == "deepseek-chat":
            encoding = tiktoken.get_encoding("cl100k_base")
        else:
            encoding = tiktoken.encoding_for_model(model)
    except Exception:
        print("Fallback to default tokenizer")
        if tiktoken is None:
            tokens_in = 0
            tokens_out = 0
            save_token_result("default", model, tokens_in, tokens_out, messages, answer)
            return answer
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens_in = len(encoding.encode(system_prompt + prompt))
    tokens_out = len(encoding.encode(answer))
    _ = calculate_cost(model, tokens_in, tokens_out)

    save_token_result("default", model, tokens_in, tokens_out, messages, answer)
    return answer


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


class ProjectManager:
    def __init__(self, project_dir: Path):
        self.paths = ProjectPaths(project_dir.resolve())

    def load_json(self, path: Path, default=None):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {} if default is None else default

    def save_json(self, path: Path, data: Any):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class EnvInstaller:
    def __init__(self, pm: ProjectManager):
        self.pm = pm

    def setup(self, force: bool = False) -> Dict[str, Any]:
        req = self.pm.paths.root / "requirements.txt"
        env_name = f"{self.pm.paths.root.name}_env"
        conda = shutil.which("conda")

        info = {
            "name": env_name,
            "conda_path": None,
            "packages": [],
            "requirements_file": str(req) if req.exists() else None,
            "status": "SKIPPED",
        }

        if req.exists():
            info["packages"] = [line.strip() for line in req.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]

        if conda and req.exists():
            cmd = [conda, "create", "-y", "-n", env_name, "--file", str(req)]
            if force:
                subprocess.run([conda, "env", "remove", "-y", "-n", env_name], check=False)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode == 0:
                info["status"] = "READY"
            else:
                info["status"] = "FAILED"
                info["error"] = proc.stderr[-2000:]
        elif not conda:
            info["status"] = "CONDA_NOT_FOUND"

        self.pm.save_json(self.pm.paths.env_info, info)
        return info


class ExperimentScanner:
    def __init__(self, pm: ProjectManager):
        self.pm = pm

    def _scan_python(self, path: Path) -> Optional[Dict[str, str]]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            return None

        funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        has_main_guard = False
        for n in ast.walk(tree):
            if isinstance(n, ast.If):
                if isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name):
                    if n.test.left.id == "__name__":
                        has_main_guard = True

        if has_main_guard or {"main", "train", "run"} & funcs:
            entry = "main" if "main" in funcs else ("train" if "train" in funcs else "run")
            return {"name": path.stem, "path": str(path.relative_to(self.pm.paths.root)), "entry": entry, "type": "python"}
        return None

    def scan(self) -> List[Dict[str, str]]:
        records: List[Dict[str, str]] = []
        for p in self.pm.paths.root.rglob("*.py"):
            if ".git" in p.parts or "venv" in p.parts or "__pycache__" in p.parts:
                continue
            rec = self._scan_python(p)
            if rec:
                records.append(rec)
        for p in self.pm.paths.root.rglob("*.ipynb"):
            records.append({"name": p.stem, "path": str(p.relative_to(self.pm.paths.root)), "entry": "notebook", "type": "notebook"})

        self.pm.save_json(self.pm.paths.registry, records)
        return records


class ConceptHandler:
    def __init__(self, pm: ProjectManager):
        self.pm = pm

    def load(self, concept_file: Optional[str]) -> Dict[str, Any]:
        if concept_file:
            cpath = Path(concept_file)
            if cpath.suffix.lower() == ".json":
                concept = json.loads(cpath.read_text(encoding="utf-8"))
            else:
                concept = {"idea": cpath.read_text(encoding="utf-8")}
        elif self.pm.paths.concept.exists():
            concept = json.loads(self.pm.paths.concept.read_text(encoding="utf-8"))
        else:
            concept = {"idea": "baseline experiment", "target_metric": "accuracy"}

        self.pm.save_json(self.pm.paths.concept, concept)
        return concept


class ExperimentPlanner:
    def __init__(self, pm: ProjectManager):
        self.pm = pm

    def create_plan(self, concept: Dict[str, Any], run_id: Optional[str] = None, output: Optional[Path] = None) -> Dict[str, Any]:
        registry = self.pm.load_json(self.pm.paths.registry, [])
        run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        steps = []
        for rec in registry:
            if rec["type"] != "python":
                continue
            params = {"idea": concept.get("idea", "baseline")}
            if "budget" in concept and isinstance(concept["budget"], dict):
                params.update(concept["budget"])
            steps.append(
                {
                    "name": rec["name"],
                    "script": rec["path"],
                    "params": params,
                    "env": self.pm.load_json(self.pm.paths.env_info, {}).get("name"),
                }
            )

        plan = {"plan_id": run_id, "steps": steps, "objective": concept.get("target_metric", "accuracy")}
        (output or self.pm.paths.plan).write_text(yaml.safe_dump(plan, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return plan


class DataRecorder:
    def __init__(self, pm: ProjectManager):
        self.pm = pm

    def init_run_dir(self, run_id: str) -> Path:
        run_dir = self.pm.paths.results / run_id
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_metrics(self, run_dir: Path, metrics: Dict[str, Any]):
        (run_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


class ExperimentRunner:
    def __init__(self, pm: ProjectManager):
        self.pm = pm
        self.recorder = DataRecorder(pm)

    @staticmethod
    def _params_to_argv(params: Dict[str, Any]) -> List[str]:
        argv = []
        for k, v in params.items():
            argv.extend([f"--{k}", str(v)])
        return argv

    def run(self, plan_file: Optional[str] = None) -> Dict[str, Any]:
        pfile = Path(plan_file) if plan_file else self.pm.paths.plan
        if not pfile.exists():
            raise FileNotFoundError(f"Plan file not found: {pfile}")
        plan = yaml.safe_load(pfile.read_text(encoding="utf-8"))
        run_id = plan["plan_id"]
        run_dir = self.recorder.init_run_dir(run_id)
        (run_dir / "config.yaml").write_text(yaml.safe_dump(plan, allow_unicode=True, sort_keys=False), encoding="utf-8")
        log_path = run_dir / "logs" / "run.log"

        metrics: Dict[str, Any] = {"run_id": run_id, "status": "SUCCESS", "steps": []}
        with log_path.open("w", encoding="utf-8") as logf:
            for step in plan.get("steps", []):
                script = self.pm.paths.root / step["script"]
                if not script.exists():
                    metrics["steps"].append({"name": step["name"], "status": "FAILED", "reason": "script not found"})
                    metrics["status"] = "FAILED"
                    continue
                cmd = [sys.executable, str(script)] + self._params_to_argv(step.get("params", {}))
                logf.write(f"\n$ {' '.join(cmd)}\n")
                proc = subprocess.run(cmd, cwd=self.pm.paths.root, capture_output=True, text=True)
                logf.write(proc.stdout)
                logf.write(proc.stderr)
                step_status = "SUCCESS" if proc.returncode == 0 else "FAILED"
                metrics["steps"].append({"name": step["name"], "status": step_status, "returncode": proc.returncode})
                if proc.returncode != 0:
                    metrics["status"] = "FAILED"

        self.recorder.write_metrics(run_dir, metrics)
        return metrics


class IterativeOptimizer:
    def __init__(self, pm: ProjectManager):
        self.pm = pm
        self.planner = ExperimentPlanner(pm)

    def iterate(self, run_id: str, concept: Dict[str, Any]) -> Dict[str, Any]:
        prev_metrics = self.pm.load_json(self.pm.paths.results / run_id / "metrics.json", {})
        budget = concept.get("budget", {})
        if isinstance(budget, dict) and "epochs" in budget:
            budget["epochs"] = int(budget["epochs"]) + 5
        else:
            budget["epochs"] = 10
        concept = {**concept, "budget": budget, "prev_status": prev_metrics.get("status")}
        next_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_iter"
        return self.planner.create_plan(concept, run_id=next_id, output=self.pm.paths.next_plan)


class Reporter:
    def __init__(self, pm: ProjectManager):
        self.pm = pm

    def generate(self, run_id: str, output_file: Optional[str] = None) -> Path:
        run_dir = self.pm.paths.results / run_id
        metrics = self.pm.load_json(run_dir / "metrics.json", {})
        cfg_text = (run_dir / "config.yaml").read_text(encoding="utf-8") if (run_dir / "config.yaml").exists() else ""
        log_tail = ""
        log_file = run_dir / "logs" / "run.log"
        if log_file.exists():
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            log_tail = "\n".join(lines[-50:])

        report = f"# Report: {run_id}\n\n"
        report += f"## Status\n\n- Overall: **{metrics.get('status', 'UNKNOWN')}**\n\n"
        report += "## Metrics (raw)\n\n```json\n" + json.dumps(metrics, ensure_ascii=False, indent=2) + "\n```\n\n"
        report += "## Plan Config\n\n```yaml\n" + cfg_text + "\n```\n\n"
        report += "## Log Tail\n\n```text\n" + log_tail + "\n```\n"

        self.pm.paths.reports.mkdir(exist_ok=True)
        out = Path(output_file) if output_file else self.pm.paths.reports / f"{run_id}.md"
        out.write_text(report, encoding="utf-8")
        return out


def command_init(args):
    pm = ProjectManager(Path(args.project_dir))
    pm.paths.results.mkdir(parents=True, exist_ok=True)
    pm.paths.reports.mkdir(parents=True, exist_ok=True)

    env = EnvInstaller(pm).setup(force=args.force)
    reg = ExperimentScanner(pm).scan()
    context = {
        "project_root": str(pm.paths.root),
        "initialized_at": datetime.now().isoformat(),
        "env_info": env,
        "experiment_count": len(reg),
    }
    pm.save_json(pm.paths.context, context)
    print(json.dumps(context, ensure_ascii=False, indent=2))


def command_run(args):
    pm = ProjectManager(Path("."))
    concept = ConceptHandler(pm).load(args.concept)
    if args.plan:
        plan_file = args.plan
    else:
        if not pm.paths.plan.exists():
            ExperimentPlanner(pm).create_plan(concept)
        plan_file = str(pm.paths.plan)
    result = ExperimentRunner(pm).run(plan_file=plan_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def command_status(args):
    pm = ProjectManager(Path("."))
    ctx = pm.load_json(pm.paths.context, {})
    runs = []
    if pm.paths.results.exists():
        for d in sorted(pm.paths.results.iterdir()):
            if d.is_dir():
                m = pm.load_json(d / "metrics.json", {})
                runs.append({"run_id": d.name, "status": m.get("status", "PENDING")})
    out = {"context": ctx, "runs": runs}
    if args.verbose:
        out["registry"] = pm.load_json(pm.paths.registry, [])
    print(json.dumps(out, ensure_ascii=False, indent=2))


def command_report(args):
    pm = ProjectManager(Path("."))
    out = Reporter(pm).generate(args.run_id, args.output)
    print(str(out))


def command_iterate(args):
    pm = ProjectManager(Path("."))
    concept = ConceptHandler(pm).load(args.concept)
    plan = IterativeOptimizer(pm).iterate(args.run_id, concept)
    print(yaml.safe_dump(plan, allow_unicode=True, sort_keys=False))
    if args.execute:
        res = ExperimentRunner(pm).run(plan_file=str(pm.paths.next_plan))
        print(json.dumps(res, ensure_ascii=False, indent=2))


def command_config(args):
    pm = ProjectManager(Path("."))
    cfg = {}
    if pm.paths.config.exists():
        cfg = yaml.safe_load(pm.paths.config.read_text(encoding="utf-8")) or {}
    if args.set:
        key, value = args.set.split("=", 1)
        cfg[key] = value
        pm.paths.config.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))


def build_parser():
    parser = argparse.ArgumentParser(prog="deepcli", description="CLI multi-agent system for automated research experiments")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize project context/environment/registry")
    p_init.add_argument("project_dir")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=command_init)

    p_run = sub.add_parser("run", help="Execute experiment plan")
    p_run.add_argument("--plan", default=None)
    p_run.add_argument("--concept", default=None)
    p_run.set_defaults(func=command_run)

    p_status = sub.add_parser("status", help="Show project status")
    p_status.add_argument("--verbose", action="store_true")
    p_status.set_defaults(func=command_status)

    p_report = sub.add_parser("report", help="Generate report for a run")
    p_report.add_argument("run_id")
    p_report.add_argument("--output", default=None)
    p_report.set_defaults(func=command_report)

    p_iter = sub.add_parser("iterate", help="Generate and optionally execute next plan")
    p_iter.add_argument("run_id")
    p_iter.add_argument("--concept", default=None)
    p_iter.add_argument("--execute", action="store_true")
    p_iter.set_defaults(func=command_iterate)

    p_cfg = sub.add_parser("config", help="Show or update config")
    p_cfg.add_argument("--set", default=None)
    p_cfg.set_defaults(func=command_config)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
