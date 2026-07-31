"""L6 · UX stability — latency, response format, error messages.

"Technically correct but unusable" is still a failure. This layer checks:
- Response latency within acceptable bounds
- Response format consistency (non-empty, reasonable length)
- Error message quality (if any errors occurred)
- Reproducibility (run N times, result should be stable)
"""

from __future__ import annotations

from src.core.models import AgentResponse, EvalCase, LayerScore


def score_stability(
    response: AgentResponse,
    case: EvalCase,
    repeat_responses: list[AgentResponse] | None = None,
) -> LayerScore:
    """Score L6: UX stability.

    Combines:
    - Latency score (0.0 if over max, linear interpolation up to max)
    - Format score (non-empty, reasonable length)
    - Reproducibility score (if repeat runs are provided)
    """
    sub_scores: dict[str, float] = {}
    details_parts: list[str] = []

    max_latency = case.max_latency_ms
    if response.latency_ms > max_latency:
        latency_score = max(0.0, 1.0 - (response.latency_ms - max_latency) / max_latency)
        details_parts.append(
            f"latency {response.latency_ms:.0f}ms exceeds {max_latency:.0f}ms"
        )
    else:
        latency_score = 1.0
    sub_scores["latency"] = round(latency_score, 2)

    text = response.text.strip()
    if not text:
        format_score = 0.0
        details_parts.append("empty response")
    elif len(text) < 10:
        format_score = 0.5
        details_parts.append("response too short")
    elif len(text) > 10000:
        format_score = 0.7
        details_parts.append("response excessively long")
    else:
        format_score = 1.0
    sub_scores["format"] = format_score

    if response.error:
        error_quality = 0.5
        details_parts.append(f"error: {response.error[:80]}")
    else:
        error_quality = 1.0
    sub_scores["error_quality"] = error_quality

    if repeat_responses and len(repeat_responses) >= 2:
        all_texts = [response.text] + [r.text for r in repeat_responses]
        if all(t == all_texts[0] for t in all_texts):
            reproducibility = 1.0
        else:
            from difflib import SequenceMatcher
            ratios = []
            for i in range(1, len(all_texts)):
                ratio = SequenceMatcher(None, all_texts[0], all_texts[i]).ratio()
                ratios.append(ratio)
            reproducibility = sum(ratios) / len(ratios) if ratios else 1.0
        sub_scores["reproducibility"] = round(reproducibility, 2)
        if reproducibility < 0.8:
            details_parts.append(f"reproducibility={reproducibility:.0%}")

        all_latencies = [response.latency_ms] + [r.latency_ms for r in repeat_responses]
        latency_var = max(all_latencies) - min(all_latencies)
        latency_stability = 1.0 - min(1.0, latency_var / max(all_latencies))
        sub_scores["latency_stability"] = round(latency_stability, 2)

        overall = (
            latency_score * 0.25
            + format_score * 0.2
            + error_quality * 0.15
            + reproducibility * 0.25
            + latency_stability * 0.15
        )
    else:
        overall = latency_score * 0.4 + format_score * 0.35 + error_quality * 0.25

    return LayerScore(
        layer="L6",
        score=round(overall, 2),
        passed=overall >= 0.5,
        details="; ".join(details_parts) or "Stability checks passed",
        sub_scores=sub_scores,
    )