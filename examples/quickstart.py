"""AgentLens Quickstart — evaluate a single Agent trajectory.

Usage:
    python examples/quickstart.py
"""

from __future__ import annotations

import asyncio

from src.core.config import AgentLensConfig
from src.core.models import (
    AgentResponse,
    CaseCategory,
    EvalCase,
    StageRecord,
)
from src.core.pipeline import SixLayerEvaluator
from src.core.report import generate_report
from src.datasets.golden_set import build_golden_set, get_case_map


class MyAgent:
    """Example agent implementation — replace with your own."""

    async def run(self, case: EvalCase) -> AgentResponse:
        text = " ".join(case.expected_response_keywords) if case.expected_response_keywords else "Here is the result."
        stages = [
            StageRecord(
                stage_id=f"s{i}",
                stage_name=name,
                success=True,
                cards=[{"name": f"card-{case.case_id}", "type": "result", "value": text[:20]}],
            )
            for i, name in enumerate(case.expected_stage_graph)
        ]
        return AgentResponse(
            case_id=case.case_id,
            text=text,
            stages=stages,
            cards=[c for s in stages for c in s.cards],
            latency_ms=1200,
            session_id=f"sess-{case.case_id}",
            tool_calls=case.expected_stage_graph,
        )


async def main() -> None:
    cases = build_golden_set()
    case_map = get_case_map(cases)

    agent = MyAgent()
    evaluator = SixLayerEvaluator(agent=agent, golden_set=cases)

    print("Running 6-layer evaluation on 40 golden test cases...")
    results = await evaluator.run()

    passed = sum(1 for r in results if r.overall_passed)
    print(f"\n{'=' * 60}")
    print(f"  Passed: {passed}/{len(results)} ({passed / len(results) * 100:.1f}%)")

    print(f"\n  Per-Layer:")
    for layer in ["L1", "L2", "L3", "L4", "L5", "L6"]:
        scores = [r.layer_scores[layer].score for r in results if layer in r.layer_scores]
        avg = sum(scores) / len(scores) if scores else 0
        bar = "#" * int(avg * 20)
        print(f"    {layer}: {avg:.2f} {bar}")

    from pathlib import Path
    output = Path("reports") / "eval_quickstart.xlsx"
    generate_report(results, output, case_map=case_map)
    print(f"\n  Report: {output}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())