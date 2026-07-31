"""Core data models for AgentLens evaluation framework.

Defines the complete type hierarchy for eval cases, agent responses,
layer scores, and evaluation results.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CaseCategory(str, Enum):
    """Golden test set categories."""
    HAPPY_PATH = "happy_path"
    AMBIGUITY = "ambiguity_recognition"
    BRAND_SENSITIVITY = "brand_memory_sensitivity"
    RETRIEVAL_GOVERNANCE = "retrieval_governance"
    STATE_CONTINUITY = "state_continuity"


class FailureLevel(str, Enum):
    """Attribution levels (L0-L7)."""
    INTERFACE_EXCEPTION = "interface_exception"
    LLM_DECOMPOSITION_ERROR = "llm_decomposition_error"
    COLOR_LOSS = "color_loss"
    PERCENTAGE_LOSS = "percentage_loss"
    FIELD_MISSING = "field_missing"
    SCENE_MISSING = "scene_missing"
    CORRECT_BUT_NO_DATA = "correct_but_no_data"
    CORRECT = "correct"


@dataclass
class EvalCase:
    """A single golden test case.

    Each case defines an expected agent behavior including:
    - What query to send
    - What stages should fire and in what order
    - What the response should contain
    - Optional adversarial conditions (brand isolation, NOT-logic, etc.)
    """
    case_id: str
    query: str
    expected_stage_graph: list[str]
    expected_response_keywords: list[str] = field(default_factory=list)
    category: CaseCategory = CaseCategory.HAPPY_PATH
    sensitive_brand: str | None = None
    not_condition: str | None = None
    max_latency_ms: float = 5000.0
    forbidden_keywords: list[str] = field(default_factory=list)
    expected_tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageRecord:
    """One stage execution record from the agent."""
    stage_id: str
    stage_name: str
    duration_ms: float = 0.0
    success: bool = True
    output: dict[str, Any] = field(default_factory=dict)
    cards: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class AgentResponse:
    """Complete response from running the agent on one eval case."""
    case_id: str
    text: str
    stages: list[StageRecord] = field(default_factory=list)
    cards: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    session_id: str | None = None
    tool_calls: list[str] = field(default_factory=list)
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def stage_names(self) -> list[str]:
        return [s.stage_name for s in self.stages]

    @property
    def stage_names_detailed(self) -> list[tuple[str, bool]]:
        return [(s.stage_name, s.success) for s in self.stages]


@dataclass
class LayerScore:
    """Score for a single evaluation layer."""
    layer: str
    score: float  # 0.0 to 1.0
    passed: bool
    details: str = ""
    sub_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class AttributionResult:
    """Result of the 8-level attribution waterfall."""
    level: FailureLevel
    description: str
    root_cause: str = ""
    suggested_fix: str = ""


@dataclass
class EvalResult:
    """Complete evaluation result for one test case."""
    case_id: str
    layer_scores: dict[str, LayerScore] = field(default_factory=dict)
    blocker: str | None = None
    attribution: AttributionResult | None = None
    latency_ms: float = 0.0
    response_text: str = ""
    overall_passed: bool = False

    @property
    def score_summary(self) -> dict[str, float]:
        return {k: v.score for k, v in self.layer_scores.items()}

    @property
    def attribution_level(self) -> str:
        return self.attribution.level.value if self.attribution else "unknown"