# 🧪 Agent Eval Tool

> Automated evaluation pipeline for multi-stage AI Agents — built during my internship at Style3D.

## What it does

- **6-layer evaluation framework** covering task completion, trajectory tracking, intermediate outputs, state consistency, security boundaries, and UX stability
- **40-item golden test set** across 5 business scenarios (happy path, ambiguity recognition, brand/memory sensitivity, search governance, state continuity)
- **0-5 Rubric + Blocker gating** mechanism for quality gates
- **8-level automated error attribution** with `rules.yaml` configuration
- **xlsx report generation** and regression comparison

## Impact

- Reduced single-round manual evaluation from **1-2 days → minutes**
- Completed **60-round regression testing** with **0 failures, 0 fallbacks, 0 prompt leaks**
- Currently used by the team for daily iteration validation

## 📁 Directory Structure

```
agent-eval-tool/
├── src/
│   ├── core/
│   │   ├── runner.py          # Evaluation runner
│   │   ├── metrics.py         # Metric computation engine
│   │   └── report.py          # Report generation
│   ├── metrics/
│   │   ├── accuracy.py        # Accuracy
│   │   ├── faithfulness.py    # Faithfulness (anti-hallucination)
│   │   ├── relevance.py       # Relevance
│   │   ├── latency.py         # Latency stats
│   │   └── cost.py            # Cost stats
│   ├── judges/
│   │   ├── llm_judge.py       # LLM-as-Judge
│   │   └── human_judge.py     # Human review interface
│   └── datasets/
│       ├── loader.py          # Dataset loader
│       └── schema.py          # Data schema
├── configs/
│   ├── default.yaml           # Default config
│   ├── rules.yaml             # 8-level error attribution rules
│   └── rubric.yaml            # 0-5 scoring rubric
├── examples/
│   ├── qa_eval.py             # QA scenario example
│   └── rag_eval.py            # RAG scenario example
├── reports/                   # Generated reports output
├── tests/
├── requirements.txt
└── README.md
```

## 💻 Core Code Snippet (sanitized)

```python
from dataclasses import dataclass
from typing import List

@dataclass
class EvalCase:
    query: str
    expected: str
    tools_available: List[str]

@dataclass
class EvalResult:
    case_id: str
    response: str
    metrics: dict
    latency_ms: float
    cost_usd: float

class AgentEvaluator:
    """6-layer Agent evaluation runner"""

    def __init__(self, agent, metrics_registry, judge):
        self.agent = agent
        self.metrics = metrics_registry
        self.judge = judge  # LLM-as-Judge or Human

    async def run(self, dataset: List[EvalCase]) -> List[EvalResult]:
        results = []
        for i, case in enumerate(dataset):
            response = await self.agent.run(
                query=case.query,
                tools=case.tools_available
            )

            metric_scores = {}
            for metric in self.metrics:
                metric_scores[metric.name] = metric.compute(
                    query=case.query,
                    response=response,
                    expected=case.expected
                )

            judge_score = await self.judge.score(
                query=case.query,
                response=response,
                reference=case.expected
            )

            results.append(EvalResult(
                case_id=f"case_{i:04d}",
                response=response,
                metrics={**metric_scores, "judge": judge_score},
                latency_ms=response.latency_ms,
                cost_usd=response.cost_usd
            ))

        return results

    def generate_report(self, results: List[EvalResult], output_path: str):
        """Generate Excel report with 3 sheets"""
        # ... export to xlsx
```

## 📊 Report Example

Running an evaluation generates `reports/eval_20260730.xlsx` with 3 sheets:

### Sheet 1: Overview

| Metric | Value |
|--------|-------|
| Total cases | 40 |
| Pass rate | 87.5% |
| Avg accuracy | 0.82 |
| Avg faithfulness | 0.91 |
| Avg relevance | 0.76 |
| LLM Judge avg | 4.2 / 5.0 |
| Avg latency | 2.3s |
| Total cost | $1.87 |

### Sheet 2: Per-case detail

| Case ID | Query | Response | Accuracy | Faithfulness | Relevance | Judge | Latency | Cost |
|---------|-------|----------|----------|--------------|-----------|-------|---------|------|
| case_0001 | How to refund? | Log in and click... | 1.0 | 0.95 | 0.90 | 5 | 1.8s | $0.01 |
| case_0002 | Where is my order? | In "My Orders"... | 1.0 | 1.0 | 0.88 | 5 | 1.2s | $0.008 |
| case_0003 | Cancel my order | Sorry, cancellation... | 0.0 | 0.70 | 0.60 | 2 | 3.1s | $0.02 |

### Sheet 3: Bad case analysis

| Case ID | Error type | Root cause | Fix suggestion |
|---------|-----------|-----------|----------------|
| case_0003 | Tool call failed | Intent "cancel" not recognized | Add intent recognition examples |
| case_0047 | Hallucination | Fabricated non-existent refund policy | Add FAQ source to RAG |
| case_0089 | Timeout | Multi-round tool calls too slow | Optimize parallel tool calls |

## 🚀 Quick Start

```bash
pip install -r requirements.txt

python -m src.core.runner \
  --config configs/default.yaml \
  --dataset examples/qa_dataset.json

open reports/eval_20260730.xlsx
```

## Tech

`Python` · `LLM-as-Judge` · `YAML` · `openpyxl` · `Agent Workflow`

## Status

This is a sanitized version of the internal tool. Sensitive business logic and company-specific configurations have been removed.

## 📄 License

MIT
