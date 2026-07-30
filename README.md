<div align="center">

# 🧪 Agent Eval Tool

**A 6-layer evaluation framework for multi-stage AI Agents — battle-tested at Style3D**

</div>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="Status" src="https://img.shields.io/badge/status-production-success?style=flat-square" />
  <img alt="Rounds" src="https://img.shields.io/badge/regression%20rounds-60-brightgreen?style=flat-square" />
  <img alt="Failures" src="https://img.shields.io/badge/failures-0-success?style=flat-square" />
  <img alt="Speedup" src="https://img.shields.io/badge/speedup-30x-blue?style=flat-square" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" />
</p>

---

## Why this exists

At Style3D I worked on a multi-stage Agent called **Style-Claw** — it takes a customer's PDF, runs through 5 stages (vision → brand enrichment → memory → retrieval → PPT generation) and outputs a sales proposal.

Every time we changed a prompt or a retrieval strategy, the team would ask: *"did this break anything?"* — and the only answer was *"let me chat with it for a few minutes and see."* That's not engineering. That's gambling.

**So I built this.** It turned "1-2 days of manual triage" into "minutes of automated report" and was used as the gating mechanism for **60 rounds of pre-release regression testing** — with **0 failures, 0 fallbacks, 0 prompt leaks**.

---

## The 6-layer evaluation framework

This isn't a generic "accuracy" metric. It's designed specifically for **multi-stage, tool-using, memory-bearing business Agents** — the kind that fail in ways single-turn chatbots never do.

| Layer | What it checks | Why it matters |
|------:|----------------|----------------|
| **L1 Task completion** | Did the Agent actually finish the job? | A pretty PPT for the wrong customer is worse than no PPT |
| **L2 Stage trajectory** | Did it hit the right stages in the right order? | Multi-stage Agents silently skip steps; this catches it |
| **L3 Intermediate card quality** | Were the intermediate cards (vision output, retrieval results) right? | Garbage in → garbage out; trace failures to their source |
| **L4 State consistency** | Session isolation, PPT asset binding, memory identity | **This was the biggest source of P0 bugs at Style3D** |
| **L5 Safety boundaries** | Prompt leakage, fallback exposure, sensitive data | One prompt leak in production = a really bad day |
| **L6 UX stability** | Latency, response format, error messages | "Technically correct but unusable" is still a failure |

---

## The 40-item golden test set

Coverage isn't "we tested 40 random prompts." It's a **deliberately adversarial** set designed to catch the specific failure modes I kept seeing in production.

| Category | Count | What it tests |
|----------|------:|---------------|
| Happy path | 10 | Baseline — does it work at all? |
| Ambiguity recognition | 6 | Does it ask for clarification vs. guessing wrong? |
| Brand / memory sensitivity | 6 | Does it confuse Customer A's brand with Customer B? |
| Retrieval governance | 10 | NOT-logic, color-material disambiguation ("麻灰" vs "麻"), zero-result handling |
| State continuity | 8 | Multi-turn state, session switching, asset binding |

Each case includes: **expected stage graph + core checkpoints + blocker conditions**.

---

## The 8-level error attribution engine

When an Agent fails, "it failed" isn't useful. You need to know *where in the chain* it failed — because the fix is completely different.

```python
# The attribution waterfall — first match wins
ATTRIBUTION_LEVELS = [
    ("interface_exception",  # L0: API timeout, model 5xx
     "The Agent never even got to think"),
    ("llm_decomposition_error",  # L1: LLM misread the query
     "Vision/understanding stage produced garbage"),
    ("color_loss",  # L2: '深蓝' silently became '蓝'
     "Color attribute dropped during extraction"),
    ("percentage_loss",  # L3: '80% 棉' became '棉'
     "Numeric attribute dropped"),
    ("field_missing",  # L4: required field absent
     "Required field absent from structured output"),
    ("scene_missing",  # L5: style/scene context absent
     "Style/scene context absent"),
    ("correct_but_no_data",  # L6: right answer, no inventory
     "Correct query, inventory just doesn't have it"),
    ("correct",  # L7: actually correct
     "Working as intended"),
]
```

This isn't theoretical — these 8 levels came from analyzing **91+ real test cases across 4 rounds of iteration** at Style3D. Each level maps to a different fix owner (infra / prompt eng / data team / business).

---

## Architecture

```
agent-eval-tool/
├── src/
│   ├── core/
│   │   ├── runner.py            # 6-layer evaluation runner
│   │   ├── metrics.py           # Per-layer metric computation
│   │   └── report.py            # xlsx report generation
│   ├── metrics/
│   │   ├── task_completion.py   # L1
│   │   ├── trajectory.py        # L2 — stage graph matching
│   │   ├── card_quality.py      # L3 — intermediate output validation
│   │   ├── state.py             # L4 — session/asset/memory isolation
│   │   ├── safety.py            # L5 — prompt leak / fallback detection
│   │   └── stability.py         # L6 — latency / format / errors
│   ├── attribution/
│   │   └── waterfall.py         # 8-level error attribution engine
│   └── datasets/
│       ├── golden_set.py        # 40-item golden test set schema
│       └── loader.py
├── configs/
│   ├── default.yaml
│   ├── rules.yaml               # 8-level attribution rules (editable)
│   └── rubric.yaml              # 0-5 scoring rubric
├── reports/                     # generated xlsx reports
├── examples/
│   ├── eval_style_claw.py       # how we used it at Style3D
│   └── eval_custom_agent.py     # how to adapt for your Agent
└── tests/
```

---

## Core runner (sanitized)

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class EvalCase:
    case_id: str
    query: str
    expected_stage_graph: List[str]   # e.g. ["vision", "brand", "memory", "search", "ppt"]
    expected_response: str
    sensitive_brand: Optional[str] = None  # for L4 brand-isolation tests
    not_condition: Optional[str] = None    # for L3 retrieval-governance tests

@dataclass
class EvalResult:
    case_id: str
    layer_scores: dict          # {"L1": 1.0, "L2": 0.8, "L3": 0.6, ...}
    blocker: Optional[str]      # if set, this case is a hard fail
    attribution: str            # one of the 8 levels
    latency_ms: float
    response: str

class SixLayerEvaluator:
    """
    The evaluator runs all 6 layers for every case, then applies the
    8-level attribution waterfall to pinpoint where the failure happened.

    Blocker gates: if any L1-L5 score is 0, the case is a hard fail
    regardless of other layer scores. This prevents "pretty failure" cases
    from passing because L6 stability was fine.
    """
    BLOCKER_LAYERS = {"L1", "L2", "L3", "L4", "L5"}

    def __init__(self, agent, golden_set, attribution_rules):
        self.agent = agent
        self.golden_set = golden_set
        self.attribution = attribution_rules  # loaded from rules.yaml

    async def run(self) -> List[EvalResult]:
        results = []
        for case in self.golden_set:
            # Run the Agent end-to-end
            agent_response = await self.agent.run(
                query=case.query,
                sensitive_context={"brand": case.sensitive_brand}
            )

            # Score each layer independently
            scores = {
                "L1": self._score_task_completion(agent_response, case),
                "L2": self._score_trajectory(agent_response.stages, case.expected_stage_graph),
                "L3": self._score_intermediate_cards(agent_response.cards, case),
                "L4": self._score_state_isolation(agent_response, case),
                "L5": self._score_safety(agent_response, case),
                "L6": self._score_stability(agent_response),
            }

            # Blocker gate: any blocker layer = 0 → hard fail
            blocker = next(
                (layer for layer in self.BLOCKER_LAYERS if scores[layer] == 0),
                None
            )

            # Attribution waterfall: first matching rule wins
            attribution = self.attribution.classify(agent_response, case)

            results.append(EvalResult(
                case_id=case.case_id,
                layer_scores=scores,
                blocker=blocker,
                attribution=attribution,
                latency_ms=agent_response.latency_ms,
                response=agent_response.text,
            ))
        return results

    def generate_report(self, results, output_path):
        """Three-sheet xlsx report:
           1. Overview (pass rate, per-layer averages, attribution histogram)
           2. Per-case detail (color-coded by attribution level)
           3. Blocker analysis (root cause + suggested fix per blocker)
        """
        ...
```

---

## Sample report (anonymized)

Running `python -m src.core.runner --config configs/default.yaml` produces `reports/eval_20260730.xlsx`:

### Sheet 1 · Overview

| Metric | Value |
|--------|------:|
| Total cases | 40 |
| Pass rate | 87.5% |
| Blocker cases | 5 |
| Avg L1 (task completion) | 0.92 |
| Avg L4 (state isolation) | 0.78 |
| Avg L5 (safety) | 0.95 |
| Attribution: `llm_decomposition_error` | 12 cases |
| Attribution: `color_loss` | 6 cases |
| Attribution: `field_missing` | 4 cases |
| Attribution: `correct` | 18 cases |
| Avg latency | 2.3s |
| Total cost | $1.87 |

### Sheet 2 · Per-case detail (color-coded)

| Case ID | Query | L1 | L2 | L3 | L4 | L5 | L6 | Attribution | Blocker |
|---------|-------|---:|---:|---:|---:|---:|---:|-------------|---------|
| c_0001 | "Summarize this brand PDF" | 1.0 | 1.0 | 0.9 | 1.0 | 1.0 | 1.0 | `correct` | — |
| c_0007 | "Find non-麻 material tops" | 1.0 | 1.0 | 0.4 | 1.0 | 1.0 | 0.9 | `color_loss` | L3 |
| c_0019 | (Brand A + Brand B in same session) | 1.0 | 0.0 | — | — | — | — | `state_contamination` | L2 |

### Sheet 3 · Blocker analysis

| Blocker case | Root cause | Suggested fix |
|--------------|-----------|----------------|
| c_0007 | "麻灰色" misread as material "麻" | Add color-material disambiguation to LLM prompt |
| c_0019 | Session asset read from latest, not session-bound | Bind asset to sessionId (P0 fix) |

---

## Impact at Style3D

| Metric | Before | After |
|--------|--------|------|
| Single-round eval time | 1-2 days manual triage | minutes (automated) |
| Pre-release regression rounds | 0 (couldn't afford the time) | **60 rounds** |
| P0 failures caught pre-release | ad-hoc | **0 escapes** |
| Prompt leaks caught | 0 (we didn't even check) | caught every time |
| Team regression culture | "did it break anything?" | "run the golden set first" |

The framework was subsequently used as the **gating mechanism** for every prompt iteration and retrieval strategy change.

---

## Roadmap

This is the **sanitized open-source version** of the internal tool. The internal version has Style3D-specific business logic; this repo aims to be a reusable framework for any multi-stage Agent.

- [x] 6-layer evaluation framework
- [x] 40-item golden test set schema
- [x] 8-level attribution engine
- [x] xlsx report generation
- [ ] **Generalize beyond Style-Claw** — currently the L3 card-quality metrics are Style-Claw-specific
- [ ] **LLM-as-Judge integration** — let a judge model score L3 card quality automatically
- [ ] **Regression diff view** — visual comparison between two eval runs
- [ ] **Community golden set** — let other vertical-industry Agent teams contribute test cases

If you're building a multi-stage Agent in a vertical industry and want to evaluate it properly, I want to talk to you. The 8-level attribution framework generalizes better than you'd expect.

---

## Status

This is a sanitized version of the internal tool used at Style3D. Sensitive business logic, customer data, and Style3D-specific configurations have been removed. The framework, golden set design, and attribution engine are intact.

## License

MIT — see [LICENSE](./LICENSE)
