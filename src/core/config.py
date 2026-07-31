"""Configuration for AgentLens evaluation runs."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentLensConfig:
    """Top-level configuration."""
    llm_enabled: bool = False
    llm_model: str = "deepseek-chat"
    llm_api_key: str | None = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    llm_base_url: str | None = "https://api.deepseek.com/v1"
    max_concurrent: int = 5
    card_scorer: str = "rule_based"
    output_dir: str = "reports"
    dry_run: bool = False

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AgentLensConfig":
        try:
            import yaml
        except ImportError as e:
            raise ImportError("pyyaml required for YAML config") from e

        text = Path(path).read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(text) or {}
        return cls(**data)

    @classmethod
    def from_json(cls, path: str | Path) -> "AgentLensConfig":
        import json

        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        return cls(**data)

    @property
    def output_path(self) -> Path:
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path(self.output_dir) / f"eval_{ts}.xlsx"