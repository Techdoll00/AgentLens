"""Dataset loader — load golden sets from JSON/YAML or build programmatically."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.models import CaseCategory, EvalCase
from src.datasets.golden_set import build_golden_set


def load_golden_set() -> list[EvalCase]:
    """Load the default 40-item golden set."""
    return build_golden_set()


def load_golden_set_from_json(path: str | Path) -> list[EvalCase]:
    """Load golden cases from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = []
    for item in data:
        item["category"] = CaseCategory(item.get("category", "happy_path"))
        cases.append(EvalCase(**item))
    return cases