"""Tests for L1 task completion scoring."""

from src.metrics.task_completion import score_task_completion


def test_task_completion_pass(good_response, sample_case):
    result = score_task_completion(good_response, sample_case)
    assert result.layer == "L1"
    assert result.score >= 0.5
    assert result.passed


def test_task_completion_empty_response(error_response, sample_case):
    result = score_task_completion(error_response, sample_case)
    assert result.score == 0.0
    assert not result.passed


def test_task_completion_partial_keywords(sample_case):
    from src.core.models import AgentResponse
    partial = AgentResponse(
        case_id="test-001",
        text="这里有一些直筒的新品",
        stages=[],
        latency_ms=1000,
    )
    result = score_task_completion(partial, sample_case)
    assert 0.0 <= result.score <= 0.6


def test_task_completion_no_keywords_in_case():
    from src.core.models import AgentResponse, EvalCase
    case = EvalCase(case_id="x", query="hello", expected_stage_graph=["a"])
    resp = AgentResponse(case_id="x", text="response", stages=[], latency_ms=100)
    result = score_task_completion(resp, case)
    assert result.score == 1.0


def test_task_completion_forbidden_content():
    from src.core.models import AgentResponse, CaseCategory, EvalCase
    case = EvalCase(
        case_id="x",
        query="test",
        expected_stage_graph=["a"],
        forbidden_keywords=["INTERNAL_SECRET"],
    )
    resp = AgentResponse(
        case_id="x",
        text="Here is INTERNAL_SECRET data",
        stages=[],
        latency_ms=100,
    )
    result = score_task_completion(resp, case)
    assert result.score == 0.0