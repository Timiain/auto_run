from __future__ import annotations

import json
from pathlib import Path

from deepcli.core.io import write_json


class ConceptHandler:
    def __init__(self, pm):
        self.pm = pm

    def load(self, concept_file: str | None):
        if concept_file:
            cpath = Path(concept_file)
            if cpath.suffix.lower() == ".json":
                concept = json.loads(cpath.read_text(encoding="utf-8"))
            else:
                concept = {"idea": cpath.read_text(encoding="utf-8")}
        elif self.pm.paths.concept.exists():
            concept = json.loads(self.pm.paths.concept.read_text(encoding="utf-8"))
        else:
            concept = {"idea": "baseline experiment", "target_metric": "accuracy", "budget": {"epochs": 5}}

        write_json(self.pm.paths.concept, concept)
        return concept
