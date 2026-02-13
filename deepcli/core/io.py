from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:
    class _YamlCompat:
        @staticmethod
        def safe_dump(data, allow_unicode=True, sort_keys=False):
            import json as _json
            return _json.dumps(data, ensure_ascii=not allow_unicode, indent=2)

        @staticmethod
        def safe_load(text):
            import json as _json
            t = (text or "").strip()
            return _json.loads(t) if t else {}

    yaml = _YamlCompat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_yaml(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
