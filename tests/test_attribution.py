"""Tests for the 8-level attribution waterfall."""

from src.attribution.waterfall import AttributionWaterfall
from src.core.models import (
    AgentResponse,
    CaseCategory,
    EvalCase,
    EvalResult,
    FailureLevel,
    LayerScore,
    StageRecord,
)


def test_attribution_interface_exception(error_response, sample_case):
    waterfall = AttributionWaterfall()
    eval_result = EvalResult(
        case_id="test-003",
        layer_scores={"L1": LayerScore("L1", 0.0, False, "error")},
    )
    result = waterfall.classify(error_response, sample_case, eval_result)
    assert result.level == FailureLevel.INTERFACE_EXCEPTION


def test_attribution_color_loss(failed_response):
    case = EvalCase(
        case_id="test-color",
        query="找麻灰色和深蓝色的面料",
        expected_stage_graph=["vision", "search"],
        expected_response_keywords=["麻灰", "深蓝"],
        category=CaseCategory.RETRIEVAL_GOVERNANCE,
    )
    waterfall = AttributionWaterfall()
    eval_result = EvalResult(
        case_id="test-color",
        layer_scores={
            "L1": LayerScore("L1", 0.3, False, "partial"),
            "L3": LayerScore("L3", 0.3, False, "color missing"),
        },
    )
    result = waterfall.classify(failed_response, case, eval_result)
    # L2 check fires first if L2=0, but eval_result L2 isn't 0 here
    # L1 isn't 0 either, so should reach color_loss
    assert result.level == FailureLevel.COLOR_LOSS


def test_attribution_correct(good_response, sample_case):
    eval_result = EvalResult(
        case_id="test-001",
        layer_scores={
            "L1": LayerScore("L1", 1.0, True),
            "L2": LayerScore("L2", 1.0, True),
            "L3": LayerScore("L3", 0.9, True),
            "L4": LayerScore("L4", 1.0, True),
            "L5": LayerScore("L5", 1.0, True),
            "L6": LayerScore("L6", 1.0, True),
        },
    )
    waterfall = AttributionWaterfall()
    result = waterfall.classify(good_response, sample_case, eval_result)
    assert result.level == FailureLevel.CORRECT


def test_attribution_field_missing():
    case = EvalCase(
        case_id="test-field",
        query="找产品",
        expected_stage_graph=["search"],
    )
    response = AgentResponse(
        case_id="test-field",
        text="找到了一些产品",
        stages=[StageRecord(stage_id="s0", stage_name="search", success=True)],
        cards=[{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}],
        latency_ms=500,
    )
    eval_result = EvalResult(
        case_id="test-field",
        layer_scores={
            "L1": LayerScore("L1", 1.0, True),
            "L2": LayerScore("L2", 1.0, True),
            "L3": LayerScore("L3", 0.3, False, "completeness=0.0", {"completeness": 0.0}),
        },
    )
    waterfall = AttributionWaterfall()
    result = waterfall.classify(response, case, eval_result)
    assert result.level == FailureLevel.FIELD_MISSING


def test_attribution_all_levels_described():
    assert len(AttributionWaterfall.LEVEL_DESCRIPTIONS) == 8
    assert len(AttributionWaterfall.FIX_SUGGESTIONS) == 8