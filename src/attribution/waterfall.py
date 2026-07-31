"""8-level error attribution waterfall — first match wins.

When an Agent fails, "it failed" is useless. You need to know *where in
the chain* it failed, because the fix owner is completely different per level:

  L0  interface_exception    → Infra team (API timeout, model 5xx)
  L1  llm_decomposition_error → Prompt eng (LLM misread the query)
  L2  color_loss             → Prompt eng (color attribute dropped)
  L3  percentage_loss         → Prompt eng (numeric attribute dropped)
  L4  field_missing           → Data team (required field absent)
  L5  scene_missing           → Data team (style/scene context absent)
  L6  correct_but_no_data    → Business (right query, inventory empty)
  L7  correct                → Working as intended

These 8 levels came from analyzing 91+ real test cases across 4 rounds
of iteration in production. Each level maps to a different fix owner.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.core.models import (
    AgentResponse,
    AttributionResult,
    CaseCategory,
    EvalCase,
    EvalResult,
    FailureLevel,
)

logger = logging.getLogger(__name__)


_COLOR_TERMS = [
    "深蓝", "浅蓝", "深灰", "浅灰", "麻灰", "墨绿", "藏青",
    "卡其", "酒红", "宝蓝", "焦糖", "black", "white", "navy",
    "cream", "olive", "beige",
]

_PERCENTAGE_RE = re.compile(r"(\d+)%\s*(棉|涤|麻|丝|羊毛|纶|polyester|cotton)")
_BRAND_NAMES = ["BrandA", "BrandB", "BrandC", "Nike", "Adidas", "Zara", "H&M", "Uniqlo"]


@dataclass
class AttributionConfig:
    """Configurable thresholds for attribution rules."""
    color_terms: list[str] = field(default_factory=lambda: _COLOR_TERMS.copy())
    percentage_pattern: str = r"(\d+)%\s*(棉|涤|麻|丝|羊毛|纶|polyester|cotton)"
    brand_names: list[str] = field(default_factory=lambda: _BRAND_NAMES.copy())


class AttributionWaterfall:
    """8-level error attribution engine.

    The waterfall checks each level in order. The first matching rule
    claims attribution for the failure. This is deliberate: it mirrors
    the causal chain — if the API is down (L0), there's no point
    checking whether color was preserved (L2).

    Usage::

        waterfall = AttributionWaterfall()
        result = waterfall.classify(response, case, eval_result)
        print(result.level)  # e.g. FailureLevel.COLOR_LOSS
    """

    LEVEL_DESCRIPTIONS = {
        FailureLevel.INTERFACE_EXCEPTION: "The Agent never even got to think",
        FailureLevel.LLM_DECOMPOSITION_ERROR: "Vision/understanding stage produced garbage",
        FailureLevel.COLOR_LOSS: "Color attribute dropped during extraction",
        FailureLevel.PERCENTAGE_LOSS: "Numeric attribute dropped",
        FailureLevel.FIELD_MISSING: "Required field absent from structured output",
        FailureLevel.SCENE_MISSING: "Style/scene context absent",
        FailureLevel.CORRECT_BUT_NO_DATA: "Correct query, inventory just doesn't have it",
        FailureLevel.CORRECT: "Working as intended",
    }

    FIX_SUGGESTIONS = {
        FailureLevel.INTERFACE_EXCEPTION: "Check API availability, retry with backoff, increase timeout",
        FailureLevel.LLM_DECOMPOSITION_ERROR: "Improve LLM prompt clarity, add few-shot examples for query understanding",
        FailureLevel.COLOR_LOSS: "Add color-material disambiguation to LLM prompt (麻灰 vs 麻)",
        FailureLevel.PERCENTAGE_LOSS: "Add numeric extraction step with regex post-processing",
        FailureLevel.FIELD_MISSING: "Add required field validation + fallback in output schema",
        FailureLevel.SCENE_MISSING: "Enrich retrieval index with style/scene metadata",
        FailureLevel.CORRECT_BUT_NO_DATA: "Business decision: expand inventory or refine query constraints",
        FailureLevel.CORRECT: "No fix needed — case working as intended",
    }

    def __init__(self, config: AttributionConfig | None = None) -> None:
        self.config = config or AttributionConfig()
        self._percentage_re = re.compile(self.config.percentage_pattern)

    def classify(
        self,
        response: AgentResponse,
        case: EvalCase,
        eval_result: EvalResult | None = None,
    ) -> AttributionResult:
        """Run the attribution waterfall — first match wins."""
        levels = [
            self._check_interface_exception,
            self._check_llm_decomposition_error,
            self._check_color_loss,
            self._check_percentage_loss,
            self._check_field_missing,
            self._check_scene_missing,
            self._check_correct_but_no_data,
            self._check_correct,
        ]

        for check_fn in levels:
            result = check_fn(response, case, eval_result)
            if result is not None:
                return result

        return AttributionResult(
            level=FailureLevel.CORRECT,
            description=self.LEVEL_DESCRIPTIONS[FailureLevel.CORRECT],
            root_cause="No specific failure detected",
            suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.CORRECT],
        )

    def _check_interface_exception(
        self, response: AgentResponse, case: EvalCase, eval_result: EvalResult | None
    ) -> AttributionResult | None:
        if response.error or not response.text.strip():
            return AttributionResult(
                level=FailureLevel.INTERFACE_EXCEPTION,
                description=self.LEVEL_DESCRIPTIONS[FailureLevel.INTERFACE_EXCEPTION],
                root_cause=response.error or "Empty response",
                suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.INTERFACE_EXCEPTION],
            )
        if eval_result and eval_result.layer_scores.get("L1", None):
            l1 = eval_result.layer_scores["L1"]
            if l1.score == 0.0 and "error" in l1.details.lower():
                return AttributionResult(
                    level=FailureLevel.INTERFACE_EXCEPTION,
                    description=self.LEVEL_DESCRIPTIONS[FailureLevel.INTERFACE_EXCEPTION],
                    root_cause=l1.details,
                    suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.INTERFACE_EXCEPTION],
                )
        return None

    def _check_llm_decomposition_error(
        self, response: AgentResponse, case: EvalCase, eval_result: EvalResult | None
    ) -> AttributionResult | None:
        if eval_result and eval_result.layer_scores.get("L2", None):
            l2 = eval_result.layer_scores["L2"]
            if l2.score == 0.0:
                return AttributionResult(
                    level=FailureLevel.LLM_DECOMPOSITION_ERROR,
                    description=self.LEVEL_DESCRIPTIONS[FailureLevel.LLM_DECOMPOSITION_ERROR],
                    root_cause=l2.details,
                    suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.LLM_DECOMPOSITION_ERROR],
                )
        if case.not_condition and case.not_condition.lower() in response.text.lower():
            return AttributionResult(
                level=FailureLevel.LLM_DECOMPOSITION_ERROR,
                description="Agent ignored NOT-condition in query",
                root_cause=f"NOT-condition '{case.not_condition}' violated",
                suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.LLM_DECOMPOSITION_ERROR],
            )
        return None

    def _check_color_loss(
        self, response: AgentResponse, case: EvalCase, eval_result: EvalResult | None
    ) -> AttributionResult | None:
        query_colors = [
            c for c in self.config.color_terms if c.lower() in case.query.lower()
        ]
        if not query_colors:
            return None

        response_text = response.text.lower()
        cards_text = json.dumps(response.cards, ensure_ascii=False).lower()

        lost = [c for c in query_colors if c.lower() not in response_text and c.lower() not in cards_text]
        if lost:
            return AttributionResult(
                level=FailureLevel.COLOR_LOSS,
                description=self.LEVEL_DESCRIPTIONS[FailureLevel.COLOR_LOSS],
                root_cause=f"Colors lost: {lost} (query had: {query_colors})",
                suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.COLOR_LOSS],
            )
        return None

    def _check_percentage_loss(
        self, response: AgentResponse, case: EvalCase, eval_result: EvalResult | None
    ) -> AttributionResult | None:
        query_matches = self._percentage_re.findall(case.query)
        if not query_matches:
            return None

        response_text = response.text.lower()
        cards_text = json.dumps(response.cards, ensure_ascii=False).lower()

        lost = []
        for num, unit in query_matches:
            if f"{num}%" not in response_text and f"{num}%" not in cards_text:
                lost.append(f"{num}%{unit}")

        if lost:
            return AttributionResult(
                level=FailureLevel.PERCENTAGE_LOSS,
                description=self.LEVEL_DESCRIPTIONS[FailureLevel.PERCENTAGE_LOSS],
                root_cause=f"Percentages lost: {lost}",
                suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.PERCENTAGE_LOSS],
            )
        return None

    def _check_field_missing(
        self, response: AgentResponse, case: EvalCase, eval_result: EvalResult | None
    ) -> AttributionResult | None:
        if eval_result and eval_result.layer_scores.get("L3", None):
            l3 = eval_result.layer_scores["L3"]
            if l3.score < 0.5 and "completeness" in l3.sub_scores:
                if l3.sub_scores["completeness"] < 0.6:
                    return AttributionResult(
                        level=FailureLevel.FIELD_MISSING,
                        description=self.LEVEL_DESCRIPTIONS[FailureLevel.FIELD_MISSING],
                        root_cause=l3.details,
                        suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.FIELD_MISSING],
                    )

        if response.cards:
            missing_field_cards = sum(
                1 for c in response.cards
                if not any(k in c for k in ("name", "value", "type", "id"))
            )
            if missing_field_cards / len(response.cards) > 0.3:
                return AttributionResult(
                    level=FailureLevel.FIELD_MISSING,
                    description=self.LEVEL_DESCRIPTIONS[FailureLevel.FIELD_MISSING],
                    root_cause=f"{missing_field_cards}/{len(response.cards)} cards missing required fields",
                    suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.FIELD_MISSING],
                )
        return None

    def _check_scene_missing(
        self, response: AgentResponse, case: EvalCase, eval_result: EvalResult | None
    ) -> AttributionResult | None:
        if case.category == CaseCategory.BRAND_SENSITIVITY:
            if case.sensitive_brand and case.sensitive_brand.lower() not in response.text.lower():
                return AttributionResult(
                    level=FailureLevel.SCENE_MISSING,
                    description="Brand/scene context absent from response",
                    root_cause=f"Expected brand '{case.sensitive_brand}' not found",
                    suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.SCENE_MISSING],
                )
        return None

    def _check_correct_but_no_data(
        self, response: AgentResponse, case: EvalCase, eval_result: EvalResult | None
    ) -> AttributionResult | None:
        if eval_result and eval_result.layer_scores.get("L1", None):
            l1 = eval_result.layer_scores["L1"]
            if l1.score >= 0.6 and "not found" in response.text.lower():
                return AttributionResult(
                    level=FailureLevel.CORRECT_BUT_NO_DATA,
                    description=self.LEVEL_DESCRIPTIONS[FailureLevel.CORRECT_BUT_NO_DATA],
                    root_cause="Agent query was correct but no matching inventory/results",
                    suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.CORRECT_BUT_NO_DATA],
                )
        return None

    def _check_correct(
        self, response: AgentResponse, case: EvalCase, eval_result: EvalResult | None
    ) -> AttributionResult | None:
        if eval_result and all(
            ls.passed for ls in eval_result.layer_scores.values()
        ):
            return AttributionResult(
                level=FailureLevel.CORRECT,
                description=self.LEVEL_DESCRIPTIONS[FailureLevel.CORRECT],
                root_cause="All layers passed",
                suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.CORRECT],
            )

        if not eval_result:
            l1_ok = len(response.text.strip()) > 0 and not response.error
            if l1_ok:
                return AttributionResult(
                    level=FailureLevel.CORRECT,
                    description=self.LEVEL_DESCRIPTIONS[FailureLevel.CORRECT],
                    root_cause="No eval result, assuming correct",
                    suggested_fix=self.FIX_SUGGESTIONS[FailureLevel.CORRECT],
                )
        return None