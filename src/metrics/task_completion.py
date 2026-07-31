"""L1 · Task completion — did the Agent actually finish the job?

Checks whether the agent produced a non-empty, relevant response that
contains the expected keywords and doesn't contain forbidden content.
"""

from __future__ import annotations

from src.core.models import AgentResponse, CaseCategory, EvalCase, LayerScore


def score_task_completion(response: AgentResponse, case: EvalCase) -> LayerScore:
    """Score L1: did the agent complete the task?

    Returns a LayerScore with score in [0.0, 1.0]:
    - 0.0 = no response / interface error
    - 0.3 = response exists but missing all expected keywords
    - 0.6 = partial keyword match
    - 1.0 = full keyword match + no forbidden content
    """
    if response.error or not response.text.strip():
        return LayerScore(
            layer="L1",
            score=0.0,
            passed=False,
            details="Empty or errored response",
        )

    text_lower = response.text.lower()
    forbidden_hits = [kw for kw in case.forbidden_keywords if kw.lower() in text_lower]

    if forbidden_hits:
        return LayerScore(
            layer="L1",
            score=0.0,
            passed=False,
            details=f"Forbidden keywords found: {forbidden_hits}",
        )

    if not case.expected_response_keywords:
        return LayerScore(
            layer="L1",
            score=1.0 if response.text.strip() else 0.0,
            passed=True,
            details="Response present, no keyword constraints",
        )

    matched = sum(
        1 for kw in case.expected_response_keywords if kw.lower() in text_lower
    )
    total = len(case.expected_response_keywords)
    ratio = matched / total

    if ratio >= 1.0:
        score = 1.0
    elif ratio >= 0.5:
        score = 0.6
    elif ratio > 0:
        score = 0.3
    else:
        score = 0.0

    return LayerScore(
        layer="L1",
        score=score,
        passed=score > 0,
        details=f"Keyword match: {matched}/{total}",
        sub_scores={"keyword_match_ratio": ratio},
    )