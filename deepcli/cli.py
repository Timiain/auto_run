from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import yaml
except Exception:
    from deepcli.core.io import yaml

from deepcli.agents.concept import ConceptHandler
from deepcli.agents.env_installer import EnvInstaller
from deepcli.agents.optimizer import IterativeOptimizer
from deepcli.agents.planner import ExperimentPlanner
from deepcli.agents.project_manager import ProjectManager
from deepcli.agents.reporter import Reporter
from deepcli.agents.runner import ExperimentRunner
from deepcli.agents.scanner import ExperimentScanner
from deepcli.core.io import read_json, read_yaml, write_yaml


def command_init(args):
    pm = ProjectManager(Path(args.project_dir))
    pm.paths.results.mkdir(parents=True, exist_ok=True)
    pm.paths.reports.mkdir(parents=True, exist_ok=True)
    env = EnvInstaller(pm).setup(force=args.force)
    reg = ExperimentScanner(pm).scan()
    print(json.dumps(pm.bootstrap_context(env, len(reg)), ensure_ascii=False, indent=2))


def command_run(args):
    pm = ProjectManager(Path("."))
    concept = ConceptHandler(pm).load(args.concept)
    planner = ExperimentPlanner(pm)
    plan_file = args.plan
    if not plan_file:
        if not pm.paths.plan.exists():
            planner.create_plan(concept)
        plan_file = str(pm.paths.plan)
    print(json.dumps(ExperimentRunner(pm).run(plan_file), ensure_ascii=False, indent=2))


def command_status(args):
    pm = ProjectManager(Path("."))
    runs = []
    if pm.paths.results.exists():
        for d in sorted(pm.paths.results.iterdir()):
            if d.is_dir():
                m = read_json(d / "metrics.json", {})
                runs.append({"run_id": d.name, "status": m.get("status", "PENDING")})
    payload = {"context": read_json(pm.paths.context, {}), "runs": runs}
    if args.verbose:
        payload["registry"] = read_json(pm.paths.registry, [])
        payload["active_plan"] = read_yaml(pm.paths.plan, {})
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def command_report(args):
    pm = ProjectManager(Path("."))
    print(Reporter(pm).generate(args.run_id, args.output))


def command_iterate(args):
    pm = ProjectManager(Path("."))
    concept = ConceptHandler(pm).load(args.concept)
    planner = ExperimentPlanner(pm)
    next_plan = IterativeOptimizer(pm, planner).iterate(args.run_id, concept)
    print(yaml.safe_dump(next_plan, allow_unicode=True, sort_keys=False))
    if args.execute:
        print(json.dumps(ExperimentRunner(pm).run(str(pm.paths.next_plan)), ensure_ascii=False, indent=2))


def command_config(args):
    pm = ProjectManager(Path("."))
    cfg = read_yaml(pm.paths.config, {}) or {}
    if args.set:
        k, v = args.set.split("=", 1)
        cfg[k] = v
        write_yaml(pm.paths.config, cfg)
    print(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deepcli", description="CLI multi-agent system for automated research experiments")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("project_dir")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=command_init)

    p_run = sub.add_parser("run")
    p_run.add_argument("--plan", default=None)
    p_run.add_argument("--concept", default=None)
    p_run.set_defaults(func=command_run)

    p_status = sub.add_parser("status")
    p_status.add_argument("--verbose", action="store_true")
    p_status.set_defaults(func=command_status)

    p_report = sub.add_parser("report")
    p_report.add_argument("run_id")
    p_report.add_argument("--output", default=None)
    p_report.set_defaults(func=command_report)

    p_iter = sub.add_parser("iterate")
    p_iter.add_argument("run_id")
    p_iter.add_argument("--concept", default=None)
    p_iter.add_argument("--execute", action="store_true")
    p_iter.set_defaults(func=command_iterate)

    p_cfg = sub.add_parser("config")
    p_cfg.add_argument("--set", default=None)
    p_cfg.set_defaults(func=command_config)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
