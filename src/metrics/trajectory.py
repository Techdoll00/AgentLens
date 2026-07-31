"""L2 · Stage trajectory — did the Agent hit the right stages in the right order?

Multi-stage Agents silently skip steps. This module performs stage-graph
matching to detect missing, extra, or out-of-order stages.
"""

from __future__ import annotations

from src.core.models import AgentResponse, EvalCase, LayerScore


def _longest_common_subsequence(a: list[str], b: list[str]) -> int:
    """Compute LCS length for sequence comparison."""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def score_trajectory(response: AgentResponse, case: EvalCase) -> LayerScore:
    """Score L2: stage trajectory correctness.

    Checks:
    1. All expected stages are present
    2. Stages fire in the expected order (LCS ratio)
    3. No unexpected stages
    """
    expected = case.expected_stage_graph
    actual = response.stage_names

    if not actual and expected:
        return LayerScore(
            layer="L2",
            score=0.0,
            passed=False,
            details="No stages executed",
        )

    if not expected:
        return LayerScore(
            layer="L2",
            score=1.0,
            passed=True,
            details="No stage graph constraints",
        )

    expected_set = set(expected)
    actual_set = set(actual)

    missing = expected_set - actual_set
    extra = actual_set - expected_set
    lcs_len = _longest_common_subsequence(actual, expected)
    order_ratio = lcs_len / len(expected) if expected else 1.0
    coverage = len(expected_set & actual_set) / len(expected_set) if expected_set else 1.0

    if missing:
        return LayerScore(
            layer="L2",
            score=0.0,
            passed=False,
            details=f"Missing stages: {sorted(missing)}",
            sub_scores={
                "coverage": coverage,
                "order_ratio": order_ratio,
                "missing_count": len(missing),
            },
        )

    if extra:
        penalty = 0.15 * len(extra)
        score = max(0.0, order_ratio - penalty)
    else:
        score = order_ratio

    return LayerScore(
        layer="L2",
        score=round(score, 2),
        passed=score >= 0.6,
        details=f"Order match: {lcs_len}/{len(expected)}, extra: {sorted(extra)}",
        sub_scores={
            "coverage": coverage,
            "order_ratio": round(order_ratio, 2),
        },
    )