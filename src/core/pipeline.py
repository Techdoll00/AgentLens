"""Six-layer evaluation pipeline — the core orchestrator.

Runs all 6 layers for every case, applies blocker gates (L1-L5 any zero
= hard fail), then runs the 8-level attribution waterfall to pinpoint
where the failure happened.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

from src.attribution.waterfall import AttributionWaterfall
from src.core.models import AgentResponse, EvalCase, EvalResult, LayerScore
from src.metrics.card_quality import CardScorer, RuleBasedCardScorer, score_card_quality
from src.metrics.safety import score_safety
from src.metrics.stability import score_stability
from src.metrics.state import score_state_isolation
from src.metrics.task_completion import score_task_completion
from src.metrics.trajectory import score_trajectory

logger = logging.getLogger(__name__)

BLOCKER_LAYERS = frozenset({"L1", "L2", "L3", "L4", "L5"})


class AgentRunner(Protocol):
    """Protocol for running an agent on an eval case."""

    async def run(self, case: EvalCase) -> AgentResponse:
        """Run the agent and return its response."""
        ...


class SixLayerEvaluator:
    """The 6-layer evaluation orchestrator.

    Blocker gates: if any L1-L5 score is 0, the case is a hard fail
    regardless of other layer scores. This prevents "pretty failure"
    cases from passing because L6 stability was fine.

    Parameters
    ----------
    agent : AgentRunner
        The agent to evaluate. Must implement ``async def run(case) -> AgentResponse``.
    golden_set : list[EvalCase]
        The golden test cases.
    card_scorer : CardScorer | None
        Scorer for L3 card quality. Defaults to rule-based.
    attribution : AttributionWaterfall | None
        Attribution engine. Defaults to standard.
    """

    def __init__(
        self,
        agent: AgentRunner,
        golden_set: list[EvalCase],
        *,
        card_scorer: CardScorer | None = None,
        attribution: AttributionWaterfall | None = None,
    ) -> None:
        self.agent = agent
        self.golden_set = golden_set
        self._card_scorer = card_scorer or RuleBasedCardScorer()
        self._attribution = attribution or AttributionWaterfall()

    async def _run_single(
        self,
        case: EvalCase,
        all_responses: dict[str, AgentResponse],
    ) -> EvalResult:
        """Run 6-layer evaluation on a single case."""
        response = await self.agent.run(case)
        all_responses[case.case_id] = response

        other_responses = [
            r for cid, r in all_responses.items()
            if cid != case.case_id
        ]

        scores: dict[str, LayerScore] = {
            "L1": score_task_completion(response, case),
            "L2": score_trajectory(response, case),
            "L3": score_card_quality(response, case, self._card_scorer),
            "L4": score_state_isolation(response, case, other_responses),
            "L5": score_safety(response, case),
            "L6": score_stability(response, case),
        }

        blocker = next(
            (layer for layer in BLOCKER_LAYERS if scores[layer].score == 0.0),
            None,
        )

        if any(ls.score < 1.0 for ls in scores.values()):
            partial = EvalResult(
                case_id=case.case_id,
                layer_scores=scores,
                blocker=blocker,
            )
            attribution = self._attribution.classify(response, case, partial)
        else:
            attribution = self._attribution.classify(response, case, EvalResult(
                case_id=case.case_id,
                layer_scores=scores,
                blocker=blocker,
            ))

        overall_passed = blocker is None and all(ls.passed for ls in scores.values())

        return EvalResult(
            case_id=case.case_id,
            layer_scores=scores,
            blocker=blocker,
            attribution=attribution,
            latency_ms=response.latency_ms,
            response_text=response.text,
            overall_passed=overall_passed,
        )

    async def run(self) -> list[EvalResult]:
        """Run the full 6-layer evaluation on all golden cases."""
        all_responses: dict[str, AgentResponse] = {}

        semaphore = asyncio.Semaphore(5)

        async def _guarded(case: EvalCase) -> EvalResult:
            async with semaphore:
                try:
                    return await self._run_single(case, all_responses)
                except Exception as e:
                    logger.error("Error evaluating case %s: %s", case.case_id, e)
                    return EvalResult(
                        case_id=case.case_id,
                        layer_scores={
                            layer: LayerScore(layer=layer, score=0.0, passed=False, details=str(e))
                            for layer in ("L1", "L2", "L3", "L4", "L5", "L6")
                        },
                        blocker="L1",
                        attribution=None,
                        response_text="",
                    )

        results = await asyncio.gather(*[_guarded(c) for c in self.golden_set])

        passed = sum(1 for r in results if r.overall_passed)
        total = len(results)
        logger.info(
            "Evaluation complete: %d/%d passed (%.0f%%), %d blockers",
            passed, total, passed / total * 100 if total else 0,
            sum(1 for r in results if r.blocker is not None),
        )
        return list(results)

    def run_sync(self) -> list[EvalResult]:
        """Synchronous wrapper."""
        return asyncio.run(self.run())