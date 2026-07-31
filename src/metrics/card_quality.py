"""L3 · Intermediate card quality — were the intermediate outputs correct?

Card quality scoring uses a pluggable scorer interface:
- RuleBasedCardScorer: keyword/pattern matching (default, no LLM needed)
- LLMJudgeCardScorer: LLM-as-Judge for semantic quality (requires API key)

This is the layer where "garbage in → garbage out" failures are caught
before they propagate to the final answer.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from src.core.models import AgentResponse, EvalCase, LayerScore

logger = logging.getLogger(__name__)


class CardScorer(ABC):
    """Abstract card quality scorer."""

    @abstractmethod
    def score_cards(
        self,
        cards: list[dict[str, Any]],
        case: EvalCase,
    ) -> tuple[float, str, dict[str, float]]:
        """Score intermediate cards.

        Returns:
            (overall_score, details, sub_scores)
        """


class RuleBasedCardScorer(CardScorer):
    """Rule-based card quality scorer — no external API needed.

    Checks:
    - Card completeness (required fields present)
    - NOT-condition satisfaction (for retrieval governance cases)
    - Color attribute preservation (detects color_loss)
    - Numeric attribute preservation (detects percentage_loss)
    """

    REQUIRED_FIELDS = {"name", "value", "type"}

    def score_cards(
        self,
        cards: list[dict[str, Any]],
        case: EvalCase,
    ) -> tuple[float, str, dict[str, float]]:
        if not cards:
            return 0.0, "No intermediate cards produced", {}

        total = len(cards)
        passed = 0
        sub_scores: dict[str, float] = {}

        completeness = sum(
            1 for c in cards
            if any(f in c for f in self.REQUIRED_FIELDS)
        ) / total
        sub_scores["completeness"] = round(completeness, 2)

        if case.not_condition:
            not_violations = sum(
                1 for c in cards
                if case.not_condition.lower() in json.dumps(c, ensure_ascii=False).lower()
            )
            not_score = 1.0 - (not_violations / total) if total else 1.0
            sub_scores["not_condition_satisfied"] = round(not_score, 2)
        else:
            not_score = 1.0

        text_all = json.dumps(cards, ensure_ascii=False)
        if case.query:
            query_colors = _extract_color_terms(case.query)
            if query_colors:
                preserved = sum(1 for c in query_colors if c in text_all) / len(query_colors)
                sub_scores["color_preservation"] = round(preserved, 2)
            else:
                preserved = 1.0
        else:
            preserved = 1.0

        query_numbers = _extract_percentage_terms(case.query)
        if query_numbers:
            num_preserved = sum(1 for n in query_numbers if n in text_all) / len(query_numbers)
            sub_scores["numeric_preservation"] = round(num_preserved, 2)
        else:
            num_preserved = 1.0

        passed_count = sum(
            1 for c in cards
            if any(f in c for f in self.REQUIRED_FIELDS)
        )
        overall = (completeness * 0.4 + not_score * 0.25 + preserved * 0.2 + num_preserved * 0.15)
        overall = round(overall, 2)

        details = f"Cards: {total}, completeness={completeness:.0%}, not_cond={not_score:.0%}"
        return overall, details, sub_scores


class LLMJudgeCardScorer(CardScorer):
    """LLM-as-Judge card quality scorer — uses an OpenAI-compatible API.

    For production use with real agents. In dry-run mode, falls back to
    RuleBasedCardScorer.
    """

    JUDGE_PROMPT = """\
You are an expert evaluator for AI Agent intermediate outputs (cards).

Given the original query and the agent's intermediate cards (JSON),
score each card 1-5 on:
- Correctness: does it match the query intent?
- Completeness: are required fields present?
- Faithfulness: no hallucinated content?

Return JSON: {"overall": float(0-1), "rationale": str}
"""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._fallback = RuleBasedCardScorer()

    async def score_cards_async(
        self,
        cards: list[dict[str, Any]],
        case: EvalCase,
    ) -> tuple[float, str, dict[str, float]]:
        try:
            import json as json_mod
            user_msg = (
                f"Query: {case.query}\n"
                f"Cards: {json_mod.dumps(cards[:10], ensure_ascii=False, indent=2)}"
            )
            messages = [
                {"role": "system", "content": self.JUDGE_PROMPT},
                {"role": "user", "content": user_msg},
            ]
            raw = await self._client.generate_text(
                messages, temperature=0.0, max_tokens=512,
            )
            import json as json_mod
            extracted = raw.strip()
            if "```json" in extracted:
                start = extracted.index("```json") + 7
                end = extracted.index("```", start)
                extracted = extracted[start:end].strip()
            parsed = json_mod.loads(extracted)
            score = float(parsed.get("overall", 0.5))
            score = max(0.0, min(1.0, score))
            return score, f"LLM Judge: {parsed.get('rationale', '')}", {}
        except Exception as e:
            logger.warning("LLM judge failed, falling back to rules: %s", e)
            return self._fallback.score_cards(cards, case)


_COLOR_TERMS = {
    "深蓝", "浅蓝", "深灰", "浅灰", "麻灰", "墨绿", "藏青", "卡其",
    "酒红", "宝蓝", "焦糖", "cream", "black", "white", "navy",
}

_PERCENTAGE_PATTERN = ["%棉", "%涤", "%麻", "%丝", "%羊毛", "%纶"]


def _extract_color_terms(text: str) -> list[str]:
    return [c for c in _COLOR_TERMS if c.lower() in text.lower()]


def _extract_percentage_terms(text: str) -> list[str]:
    return [p for p in _PERCENTAGE_PATTERN if p in text]


def score_card_quality(
    response: AgentResponse,
    case: EvalCase,
    scorer: CardScorer | None = None,
) -> LayerScore:
    """Score L3: intermediate card quality."""
    scorer = scorer or RuleBasedCardScorer()
    cards = response.cards

    if not cards and response.stages:
        cards = []
        for stage in response.stages:
            cards.extend(stage.cards)

    overall, details, sub_scores = scorer.score_cards(cards, case)

    return LayerScore(
        layer="L3",
        score=overall,
        passed=overall >= 0.5,
        details=details,
        sub_scores=sub_scores,
    )