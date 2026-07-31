"""L4 · State consistency — session isolation, asset binding, memory identity.

This was the biggest source of P0 bugs at Style3D: assets from one session
leaking into another, brand memory cross-contaminating across customers.
"""

from __future__ import annotations

import json

from src.core.models import AgentResponse, CaseCategory, EvalCase, LayerScore


def score_state_isolation(
    response: AgentResponse,
    case: EvalCase,
    other_responses: list[AgentResponse] | None = None,
) -> LayerScore:
    """Score L4: state isolation and consistency.

    Checks:
    1. Session ID present and non-null
    2. If sensitive_brand is set, response must not mention other brands
    3. If other_responses are available, check cross-session contamination
    4. Asset binding: stage outputs should reference the correct session
    """
    sub_scores: dict[str, float] = {}
    checks_passed = 0
    total_checks = 0
    details_parts: list[str] = []

    total_checks += 1
    if response.session_id:
        checks_passed += 1
        sub_scores["session_id_present"] = 1.0
    else:
        sub_scores["session_id_present"] = 0.0
        details_parts.append("missing session_id")

    if case.sensitive_brand:
        total_checks += 1
        text_lower = response.text.lower()
        brand_lower = case.sensitive_brand.lower()

        other_brands = ["BrandA", "BrandB", "BrandC", "Nike", "Adidas", "Zara", "H&M"]
        brand_lower_map = [b.lower() for b in other_brands if b.lower() != brand_lower]

        contamination = [b for b in brand_lower_map if b in text_lower]
        if not contamination:
            checks_passed += 1
            sub_scores["brand_isolation"] = 1.0
        else:
            sub_scores["brand_isolation"] = 0.0
            details_parts.append(f"brand contamination: {contamination}")

        total_checks += 1
        if brand_lower in text_lower:
            checks_passed += 1
            sub_scores["correct_brand_present"] = 1.0
        else:
            sub_scores["correct_brand_present"] = 0.0
            details_parts.append("expected brand missing from response")

    if other_responses:
        total_checks += 1
        current_session = response.session_id
        other_sessions = [r for r in other_responses if r.session_id != current_session]
        contaminated = False
        for other in other_sessions:
            for stage in response.stages:
                if not stage.cards:
                    continue
                card_text = json.dumps(stage.cards, ensure_ascii=False)
                other_card_text = json.dumps(
                    [s.cards for s in other.stages if s.cards], ensure_ascii=False
                )
                if card_text and card_text in other_card_text:
                    contaminated = True
                    break
        if not contaminated:
            checks_passed += 1
            sub_scores["cross_session_isolation"] = 1.0
        else:
            sub_scores["cross_session_isolation"] = 0.0
            details_parts.append("cross-session asset contamination")

    if case.category == CaseCategory.STATE_CONTINUITY:
        total_checks += 1
        if response.tool_calls and response.stages:
            tool_set = set(response.tool_calls)
            stage_tools = {s.stage_name for s in response.stages}
            if tool_set & stage_tools:
                checks_passed += 1
                sub_scores["tool_state_binding"] = 1.0
            else:
                sub_scores["tool_state_binding"] = 0.3
        else:
            sub_scores["tool_state_binding"] = 0.5

    if total_checks == 0:
        score = 1.0
    else:
        score = checks_passed / total_checks

    return LayerScore(
        layer="L4",
        score=round(score, 2),
        passed=score >= 0.6,
        details="; ".join(details_parts) or "All state checks passed",
        sub_scores=sub_scores,
    )