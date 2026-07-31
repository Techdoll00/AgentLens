"""Tests for the 6-layer evaluation pipeline."""

import pytest

from src.attribution.waterfall import AttributionWaterfall
from src.core.models import (
    AgentResponse,
    CaseCategory,
    EvalCase,
    StageRecord,
)
from src.core.pipeline import BLOCKER_LAYERS, SixLayerEvaluator
from src.datasets.golden_set import build_golden_set


class StubAgent:
    """Minimal agent for pipeline tests."""

    def __init__(self, responses: dict[str, AgentResponse] | None = None) -> None:
        self._responses = responses or {}

    async def run(self, case: EvalCase) -> AgentResponse:
        if case.case_id in self._responses:
            return self._responses[case.case_id]
        text = " ".join(case.expected_response_keywords) if case.expected_response_keywords else "请补充更多信息"
        if not text.strip():
            text = "请补充更多信息"
        cards = []
        for kw in case.expected_response_keywords:
            cards.append({"name": f"item-{case.case_id}-{kw}", "type": "result", "value": kw})
        if not text.strip():
            text = "请补充更多信息"
        return AgentResponse(
            case_id=case.case_id,
            text=text,
            stages=[
                StageRecord(
                    stage_id=f"s{i}",
                    stage_name=n,
                    success=True,
                    cards=cards if i == 0 else [],
                )
                for i, n in enumerate(case.expected_stage_graph)
            ],
            cards=cards,
            latency_ms=1000,
            session_id=f"sess-{case.case_id}",
            tool_calls=case.expected_stage_graph,
        )


@pytest.mark.asyncio
async def test_pipeline_single_case():
    case = EvalCase(
        case_id="pipe-001",
        query="找深蓝色牛仔裤",
        expected_stage_graph=["vision", "search"],
        expected_response_keywords=["深蓝"],
    )
    agent = StubAgent(responses={
        "pipe-001": AgentResponse(
            case_id="pipe-001",
            text="找到了深蓝色的牛仔裤推荐",
            stages=[
                StageRecord(stage_id="s0", stage_name="vision", success=True),
                StageRecord(stage_id="s1", stage_name="search", success=True,
                            cards=[{"name": "jeans", "type": "item", "value": "深蓝"}]),
            ],
            cards=[{"name": "jeans", "type": "item", "value": "深蓝"}],
            latency_ms=1200,
            session_id="sess-pipe-001",
        )
    })
    evaluator = SixLayerEvaluator(agent=agent, golden_set=[case])
    results = await evaluator.run()

    assert len(results) == 1
    result = results[0]
    assert all(layer in result.layer_scores for layer in ("L1", "L2", "L3", "L4", "L5", "L6"))
    assert result.attribution is not None


@pytest.mark.asyncio
async def test_pipeline_blocker_detection():
    case = EvalCase(
        case_id="pipe-block",
        query="test",
        expected_stage_graph=["vision", "search"],
    )
    agent = StubAgent(responses={
        "pipe-block": AgentResponse(
            case_id="pipe-block",
            text="",
            stages=[],
            latency_ms=6000,
            error="timeout",
        )
    })
    evaluator = SixLayerEvaluator(agent=agent, golden_set=[case])
    results = await evaluator.run()

    result = results[0]
    assert result.blocker is not None
    assert result.overall_passed is False


@pytest.mark.asyncio
async def test_pipeline_full_golden_set():
    cases = build_golden_set()
    agent = StubAgent()
    evaluator = SixLayerEvaluator(agent=agent, golden_set=cases)
    results = await evaluator.run()

    assert len(results) == 40
    passed = sum(1 for r in results if r.overall_passed)
    assert passed > 0
    assert all(r.attribution is not None for r in results)


def test_blocker_layers_definition():
    assert "L1" in BLOCKER_LAYERS
    assert "L2" in BLOCKER_LAYERS
    assert "L3" in BLOCKER_LAYERS
    assert "L4" in BLOCKER_LAYERS
    assert "L5" in BLOCKER_LAYERS
    assert "L6" not in BLOCKER_LAYERS