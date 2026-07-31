"""AgentLens CLI — command-line interface for evaluation runs.

Usage:
    # Dry-run (no agent needed, generates sample report)
    python -m src.cli --dry-run

    # Real evaluation (requires an agent implementation)
    python -m src.cli --config configs/default.yaml --agent my_agent.MyAgent

    # Run with LLM-as-Judge for card quality
    python -m src.cli --config configs/default.yaml --llm-judge
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
from pathlib import Path

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

logger = logging.getLogger("agentlens")


class MockAgent:
    """Deterministic mock agent for --dry-run mode.

    Simulates realistic agent responses including:
    - Happy path cases that mostly pass
    - Intentional failures (color loss, state contamination, etc.)
    - Realistic latency variation
    """

    def __init__(self) -> None:
        self._rng = random.Random(42)

    async def run(self, case: EvalCase) -> AgentResponse:
        case_id_num = int(case.case_id.split("_")[1])
        fail_cases = {3, 7, 11, 19, 24, 33}

        if case_id_num in fail_cases:
            return self._make_failure_response(case, case_id_num)

        return self._make_success_response(case, case_id_num)

    def _make_success_response(self, case: EvalCase, num: int) -> AgentResponse:
        stages = [
            StageRecord(
                stage_id=f"s{i}",
                stage_name=name,
                duration_ms=self._rng.uniform(100, 500),
                success=True,
                output={"status": "ok", "case_id": case.case_id},
                cards=self._generate_cards(case, name, num),
            )
            for i, name in enumerate(case.expected_stage_graph)
        ]

        text_parts = []
        if case.sensitive_brand:
            text_parts.append(f"Based on {case.sensitive_brand}'s brand profile")
        if case.expected_response_keywords:
            text_parts.append(" ".join(case.expected_response_keywords))
        else:
            text_parts.append("Here are the recommended items based on your query.")
        text_parts.append("Here's the analysis and recommendations.")
        text = ". ".join(text_parts)

        return AgentResponse(
            case_id=case.case_id,
            text=text,
            stages=stages,
            cards=[card for s in stages for card in s.cards],
            latency_ms=self._rng.uniform(800, 3000),
            session_id=f"sess-{num:04d}-{case.case_id}",
            tool_calls=case.expected_stage_graph,
        )

    def _make_failure_response(self, case: EvalCase, num: int) -> AgentResponse:
        failure_type = num % 7

        if failure_type == 0:
            return AgentResponse(
                case_id=case.case_id,
                text="",
                stages=[],
                latency_ms=self._rng.uniform(5000, 8000),
                session_id=f"sess-{num:04d}-{case.case_id}",
                error="API timeout: model returned 503",
            )

        if failure_type == 1:
            stages = [
                StageRecord(stage_id="s0", stage_name="vision", success=True),
                StageRecord(stage_id="s1", stage_name="brand", success=True),
            ]
            return AgentResponse(
                case_id=case.case_id,
                text="Here's a response based on the blue jeans analysis.",
                stages=stages,
                cards=[{"name": f"jeans-{case.case_id}", "color": "蓝", "case_id": case.case_id}],
                latency_ms=self._rng.uniform(1500, 3000),
                session_id=f"sess-{num:04d}-{case.case_id}",
            )

        if failure_type == 2:
            if case.sensitive_brand and case.sensitive_brand == "BrandA":
                text = f"Based on BrandB's profile: BrandA doesn't have this style."
            else:
                text = f"Based on analysis: {case.query[:50]}"
            return AgentResponse(
                case_id=case.case_id,
                text=text,
                stages=[
                    StageRecord(stage_id=s, stage_name=n, success=True)
                    for s, n in enumerate(case.expected_stage_graph)
                ],
                cards=[{"name": f"item-{case.case_id}", "color": "unknown", "case_id": case.case_id}],
                latency_ms=self._rng.uniform(800, 2500),
                session_id=f"sess-{num:04d}-{case.case_id}",
            )

        if failure_type == 3:
            return AgentResponse(
                case_id=case.case_id,
                text="Here's the analysis result.",
                stages=[
                    StageRecord(stage_id=s, stage_name=n, success=True)
                    for s, n in enumerate(case.expected_stage_graph)
                ],
                cards=[{"id": f"1-{case.case_id}"}, {"id": f"2-{case.case_id}"}, {"id": f"3-{case.case_id}"}],
                latency_ms=self._rng.uniform(800, 2500),
                session_id=f"sess-{num:04d}-{case.case_id}",
            )

        if failure_type == 4:
            return AgentResponse(
                case_id=case.case_id,
                text="As an AI assistant, I was instructed to help you find items.",
                stages=[
                    StageRecord(stage_id=s, stage_name=n, success=True)
                    for s, n in enumerate(case.expected_stage_graph)
                ],
                cards=[{"name": f"item-{case.case_id}", "value": "test", "case_id": case.case_id}],
                latency_ms=self._rng.uniform(800, 2500),
                session_id=f"sess-{num:04d}-{case.case_id}",
            )

        if failure_type == 5:
            return AgentResponse(
                case_id=case.case_id,
                text="Here are the items. Internal error occurred. Fallback response activated.",
                stages=[
                    StageRecord(stage_id=s, stage_name=n, success=True)
                    for s, n in enumerate(case.expected_stage_graph)
                ],
                cards=[{"name": f"item-{case.case_id}", "value": "test", "case_id": case.case_id}],
                latency_ms=self._rng.uniform(800, 2500),
                session_id=f"sess-{num:04d}-{case.case_id}",
            )

        return self._make_success_response(case, num)

    def _generate_cards(self, case: EvalCase, stage_name: str, case_num: int = 0) -> list[dict]:
        cards = []
        card: dict = {"name": f"entity-{case.case_id}", "type": "result", "value": f"data-{case_num}"}

        if "麻灰" in case.query:
            card["color"] = "麻灰"
        elif "深蓝" in case.query:
            card["color"] = "深蓝"
        elif "白色" in case.query:
            card["color"] = "白色"

        if "80%棉" in case.query:
            card["material"] = "80%棉"

        if case.sensitive_brand:
            card["brand"] = case.sensitive_brand

        if stage_name in ("search", "vision"):
            cards.append(card)
        return cards


def run_dry_run() -> None:
    """Run a complete evaluation with mock data and generate a report."""
    print("=" * 60)
    print("AgentLens — Dry Run Mode")
    print("=" * 60)

    cases = build_golden_set()
    case_map = get_case_map(cases)
    mock_agent = MockAgent()

    evaluator = SixLayerEvaluator(
        agent=mock_agent,
        golden_set=cases,
    )

    print(f"\nRunning 6-layer evaluation on {len(cases)} golden test cases...")
    results = evaluator.run_sync()

    passed = sum(1 for r in results if r.overall_passed)
    blocked = sum(1 for r in results if r.blocker is not None)
    total = len(results)

    print(f"\n{'─' * 50}")
    print(f"  Total cases:  {total}")
    print(f"  Passed:       {passed} ({passed / total * 100:.1f}%)")
    print(f"  Blockers:     {blocked}")
    print(f"{'─' * 50}")

    print("\n  Per-Layer Averages:")
    for layer in ["L1", "L2", "L3", "L4", "L5", "L6"]:
        scores = [r.layer_scores[layer].score for r in results if layer in r.layer_scores]
        avg = sum(scores) / len(scores) if scores else 0
        bar = "█" * int(avg * 20)
        print(f"    {layer}: {avg:.2f} {bar}")

    print(f"\n  Attribution Distribution:")
    from collections import Counter
    attr_counter = Counter(r.attribution_level for r in results)
    for level, count in sorted(attr_counter.items(), key=lambda x: -x[1]):
        print(f"    {level:30s}  {count:3d}")

    output_path = Path("reports") / "eval_dry_run.xlsx"
    print(f"\n  Generating xlsx report → {output_path}")
    generate_report(results, output_path, case_map=case_map)
    print(f"  [OK] Report saved to {output_path}")
    print(f"\n  Open it: start {output_path}")
    print(f"{'=' * 60}")


def run_config(config_path: str, llm_judge: bool = False) -> None:
    """Run evaluation with a config file."""
    config = AgentLensConfig.from_yaml(config_path)
    cases = build_golden_set()
    case_map = get_case_map(cases)

    print(f"AgentLens — Config mode ({config_path})")
    print(f"  LLM Judge: {'enabled' if llm_judge else 'disabled'}")
    print(f"  Card scorer: {config.card_scorer}")
    print(f"  Output: {config.output_path}")

    agent = MockAgent()
    card_scorer = None

    if llm_judge:
        from src.metrics.card_quality import LLMJudgeCardScorer
        try:
            from src.llm import OpenAIClient

            client = OpenAIClient(
                model=config.llm_model,
                api_key=config.llm_api_key or "",
                base_url=config.llm_base_url,
            )
            card_scorer = LLMJudgeCardScorer(client)
        except ImportError:
            print("  ⚠ openai not installed, falling back to rule-based scorer")

    evaluator = SixLayerEvaluator(
        agent=agent,
        golden_set=cases,
        card_scorer=card_scorer,
    )

    results = evaluator.run_sync()
    output_path = config.output_path
    generate_report(results, output_path, case_map=case_map)
    print(f"  [OK] Report saved to {output_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="agentlens",
        description="AgentLens — Six-layer x-ray for AI Agent quality",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run with mock data (no agent needed, generates sample report)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config YAML file",
    )
    parser.add_argument(
        "--llm-judge",
        action="store_true",
        help="Enable LLM-as-Judge for L3 card quality scoring",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")

    if args.dry_run:
        run_dry_run()
    elif args.config:
        run_config(args.config, llm_judge=args.llm_judge)
    else:
        parser.print_help()
        print("\nTip: try `python -m src.cli --dry-run` to see a sample report!")


if __name__ == "__main__":
    main()