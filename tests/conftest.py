"""Test fixtures for AgentLens test suite."""

from __future__ import annotations

import pytest

from src.core.models import (
    AgentResponse,
    CaseCategory,
    EvalCase,
    StageRecord,
)
from src.datasets.golden_set import build_golden_set


@pytest.fixture
def sample_case() -> EvalCase:
    return EvalCase(
        case_id="test-001",
        query="找深蓝色的牛仔裤，材质80%棉",
        expected_stage_graph=["vision", "brand", "memory", "search", "ppt"],
        expected_response_keywords=["深蓝", "牛仔裤", "棉"],
        category=CaseCategory.HAPPY_PATH,
    )


@pytest.fixture
def sample_failure_case() -> EvalCase:
    return EvalCase(
        case_id="test-002",
        query="找麻灰色的面料",
        expected_stage_graph=["vision", "brand", "memory", "search"],
        expected_response_keywords=["麻灰"],
        not_condition="麻",
        category=CaseCategory.RETRIEVAL_GOVERNANCE,
    )


@pytest.fixture
def good_response() -> AgentResponse:
    return AgentResponse(
        case_id="test-001",
        text="根据深蓝色的牛仔裤分析，80%棉材质，推荐款式如下...",
        stages=[
            StageRecord(stage_id="s0", stage_name="vision", success=True,
                        cards=[{"name": "image", "type": "vision", "value": "检测到牛仔裤"}]),
            StageRecord(stage_id="s1", stage_name="brand", success=True),
            StageRecord(stage_id="s2", stage_name="memory", success=True),
            StageRecord(stage_id="s3", stage_name="search", success=True,
                        cards=[{"name": "result1", "type": "item", "value": "深蓝牛仔裤 80%棉"}]),
            StageRecord(stage_id="s4", stage_name="ppt", success=True),
        ],
        cards=[{"name": "result1", "type": "item", "value": "深蓝牛仔裤 80%棉"}],
        latency_ms=1500,
        session_id="sess-001",
        tool_calls=["vision_api", "brand_db", "search_api"],
    )


@pytest.fixture
def failed_response() -> AgentResponse:
    return AgentResponse(
        case_id="test-002",
        text="找到了蓝色的面料",
        stages=[
            StageRecord(stage_id="s0", stage_name="vision", success=True,
                        cards=[{"name": "item", "color": "蓝"}]),
            StageRecord(stage_id="s1", stage_name="brand", success=True),
            StageRecord(stage_id="s2", stage_name="memory", success=True),
            StageRecord(stage_id="s3", stage_name="search", success=True),
        ],
        cards=[{"name": "item", "color": "蓝"}],
        latency_ms=2200,
        session_id="sess-002",
    )


@pytest.fixture
def error_response() -> AgentResponse:
    return AgentResponse(
        case_id="test-003",
        text="",
        stages=[],
        latency_ms=6000,
        session_id="sess-003",
        error="API timeout: model returned 503",
    )


@pytest.fixture
def full_golden_set() -> list[EvalCase]:
    return build_golden_set()