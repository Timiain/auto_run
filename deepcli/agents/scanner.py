from __future__ import annotations

import ast

from deepcli.core.io import write_json


class ExperimentScanner:
    def __init__(self, pm):
        self.pm = pm

    @staticmethod
    def _extract_cli_args(tree: ast.AST) -> list[str]:
        """Extract argparse option names like --epochs/--lr from add_argument calls."""
        cli_args: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("--"):
                    cli_args.append(arg.value.lstrip("-").replace("-", "_"))
        return sorted(set(cli_args))

    def _scan_python(self, path):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            return None

        funcs = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        has_main_guard = any(
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            for node in ast.walk(tree)
        )
        if has_main_guard or {"main", "train", "run"} & funcs:
            entry = "main" if "main" in funcs else ("train" if "train" in funcs else "run")
            return {
                "name": path.stem,
                "path": str(path.relative_to(self.pm.paths.root)),
                "entry": entry,
                "type": "python",
                "cli_args": self._extract_cli_args(tree),
            }
        return None

    def scan(self):
        records = []
        for py in self.pm.paths.root.rglob("*.py"):
            if any(part in {".git", "venv", "__pycache__"} for part in py.parts):
                continue
            rec = self._scan_python(py)
            if rec:
                records.append(rec)
        for nb in self.pm.paths.root.rglob("*.ipynb"):
            records.append({"name": nb.stem, "path": str(nb.relative_to(self.pm.paths.root)), "entry": "notebook", "type": "notebook"})

        write_json(self.pm.paths.registry, records)
        return records
