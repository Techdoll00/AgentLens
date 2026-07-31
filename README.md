<div align="center">

# AgentLens

**Six-layer x-ray for AI Agent quality**

Inspect your Agent like a CT scan — 6 layers deep, 8-level error attribution, one-click report.

</div>

<p align="center">
  <b>English</b> · <a href="./README_CN.md">中文</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" />
  <img alt="Tests" src="https://img.shields.io/badge/tests-15%20passed-success?style=flat-square" />
  <img alt="Pass Rate" src="https://img.shields.io/badge/pass%20rate-87.5%25-success?style=flat-square" />
  <img alt="Dry Run" src="https://img.shields.io/badge/dry--run-ready-orange?style=flat-square" />
</p>

---

## You have these pains?

| Pain | What happens now | How bad is it |
|------|-------------------|---------------|
| "It works on my machine" | Agent passes your test queries but breaks on real users | P0 in production |
| "Which step caused the failure?" | Agent returns wrong answer, team argues for hours about where it broke | 1-2 days of triage per release |
| "Did this prompt change break anything?" | Nobody knows — you re-test manually every time | Fear of iteration |
| "Prompt leaked again?!" | System prompt or fallback messages exposed to users | Trust lost instantly |
| "Brand A's data showed up in Brand B's session" | Cross-session contamination in multi-tenant Agents | Silent P0, caught by customer |

**If any of this sounds familiar — AgentLens is for you.**

---

## What is AgentLens?

AgentLens is a **6-layer evaluation framework** for multi-stage AI Agents. Instead of giving a single "accuracy" score, it scans your Agent layer by layer — like a CT scan — and tells you exactly *where* it breaks and *why*.

```
                    AgentLens
                  /     |     \
               6 layers  |   8-level attribution
                  \     |     /
                   \    |    /
              ┌──────────────────┐
              │  Evaluated Agent  │
              │  (trajectory)    │
              └──────────────────┘
```

**One-liner:** Run 40 golden test cases through 6 evaluation layers, get an xlsx report with 8-level error attribution.

---

## 30-second quick start

```bash
git clone https://github.com/Techdoll00/AgentLens.git
cd AgentLens
pip install -r requirements.txt
python -m src.cli --dry-run
```

That's it. No API key needed. You'll get a 3-sheet xlsx report at `reports/eval_dry_run.xlsx`:

- **Sheet 1 — Overview**: pass rate, per-layer averages, attribution histogram
- **Sheet 2 — Case Detail**: every case scored across L1-L6, color-coded by attribution level
- **Sheet 3 — Blocker Analysis**: root cause + suggested fix for each blocker case

> The `--dry-run` uses a mock agent with realistic failure patterns. To evaluate your own Agent, implement the `AgentRunner` protocol and pass it to `SixLayerEvaluator`.

---

## The 6-layer evaluation: what each layer does

```
        ┌─────────────────┐
   L6   │  UX Stability   │  Latency, format, reproducibility
        ├─────────────────┤
   L5   │    Safety       │  Prompt leak, fallback exposure, sensitive data
        ├─────────────────┤
   L4   │  State Isolation│  Session binding, brand contamination, memory identity
        ├─────────────────┤  ← Biggest source of P0 bugs in production
   L3   │  Card Quality   │  Intermediate output correctness, NOT-logic, color/numeric preservation
        ├─────────────────┤
   L2   │   Trajectory    │  Stage graph matching — did it hit right stages in right order?
        ├─────────────────┤
   L1   │ Task Completion │  Did it actually finish the job?
        └─────────────────┘
```

**Blocker gate**: if any L1-L5 score is 0, the case is a **hard fail** — regardless of L6. No "pretty failure" passes because the response was fast.

| Layer | What it checks | Why this layer exists |
|-------|----------------|-----------------------|
| **L1** | Task completion | A pretty PPT for the wrong customer is worse than no PPT |
| **L2** | Stage trajectory | Multi-stage Agents silently skip steps; LCS matching catches it |
| **L3** | Card quality | Garbage in → garbage out; trace failures to their source stage |
| **L4** | State isolation | **Cross-session contamination is silent and catastrophic** |
| **L5** | Safety | One prompt leak = a really bad day |
| **L6** | Stability | "Technically correct but unusable" is still a failure |

---

## 8-level error attribution: "5 seconds to know where it broke"

When an Agent fails, "it failed" is useless. The attribution waterfall checks 8 levels in order — first match wins — because the fix owner is completely different per level:

```
L0  interface_exception     → Infra team (API timeout, 503)
L1  llm_decomposition_error  → Prompt eng (LLM misread the query)
L2  color_loss              → Prompt eng (深蓝 silently became 蓝)
L3  percentage_loss         → Prompt eng (80%棉 became just 棉)
L4  field_missing           → Data team (required field absent)
L5  scene_missing           → Data team (style/brand context absent)
L6  correct_but_no_data     → Business (query was right, inventory empty)
L7  correct                 → Working as intended
```

Each level maps to a different **fix owner** and **suggested fix** — the report tells you *exactly who to escalate to*.

---

## How it compares

| Feature | AgentLens | LangSmith | AgentBench | OpenAI Evals |
|---------|-----------|-----------|------------|--------------|
| **Agent trajectory scoring** | Per-step per-dimension | Tracing only | Final result only | Generic |
| **Multi-stage stage graph** | LCS matching | Manual | No | No |
| **State isolation (L4)** | Built-in | Manual | No | No |
| **Safety/prompt leak** | Built-in regex + patterns | Manual | No | No |
| **Error attribution** | 8-level waterfall | Manual | No | No |
| **Blocker gate** | L1-L5 hard fail | No | No | No |
| **Report format** | xlsx (3 sheets) | Web UI | JSON | JSON |
| **Offline / self-hosted** | Yes | No (SaaS) | Yes | Yes |
| **Free** | Yes, MIT | Paid tiers | Yes | Yes |
| **Setup time** | 1 command (dry-run) | 30+ min | Complex | Moderate |

**AgentLens is the only tool that does error attribution.** Others tell you "it failed." AgentLens tells you "it failed at level 4 because session isolation broke — fix asset binding (bind to sessionId)."

---

## Real cases (from dry-run report)

### Case 1: Color silently dropped
```
Query:  "找麻灰色的面料"  (find 麻灰 colored fabric)
Agent:  "找到了蓝色的面料"  (found blue fabric)

→ L1: 0.3 (partial keywords)
→ L3: 0.0 (color_loss detected)
→ Attribution: L2  color_loss
→ Fix: Add color-material disambiguation to LLM prompt (麻灰 ≠ 麻)
```

### Case 2: Stage trajectory skipped
```
Query:  Expected stages: [vision → brand → memory → search → ppt]
Agent:  Actual stages:   [vision → brand]

→ L2: 0.0 (missing 3 stages)
→ Attribution: L1  llm_decomposition_error
→ Fix: Improve LLM prompt clarity, add few-shot examples
```

### Case 3: Prompt leak
```
Agent response: "As an AI assistant, I was instructed to help you find items..."

→ L5: 0.0 (prompt leak detected)
→ Attribution: checking upstream
→ Fix: Review system prompt, sanitize output
```

---

## Benchmark data

Running `python -m src.cli --dry-run` on the 40-item golden set:

| Metric | Value |
|--------|------:|
| Total cases | 40 |
| Pass rate | 87.5% |
| Blocker cases | 5 |
| Avg L1 (task completion) | 0.90 |
| Avg L2 (trajectory) | 0.97 |
| Avg L3 (card quality) | 0.93 |
| Avg L4 (state isolation) | 0.99 |
| Avg L5 (safety) | 0.93 |
| Avg L6 (stability) | 0.98 |

Attribution distribution:

| Level | Count |
|-------|------:|
| `correct` | 34 |
| `color_loss` | 3 |
| `interface_exception` | 1 |
| `scene_missing` | 1 |
| `llm_decomposition_error` | 1 |

---

## The 40-item golden test set

Not random prompts. A **deliberately adversarial** set targeting specific failure modes:

| Category | Count | What it catches |
|----------|------:|----------------|
| Happy path | 10 | Baseline — does it work at all? |
| Ambiguity recognition | 6 | Does it ask for clarification vs. guess wrong? |
| Brand / memory sensitivity | 6 | Does it confuse Customer A's brand with Customer B? |
| Retrieval governance | 10 | NOT-logic, color disambiguation (麻灰 vs 麻), zero-result |
| State continuity | 8 | Multi-turn state, session switching, asset binding |

---

## Who is this for?

- **AI Agent product PMs** — need a quality gate before releasing Agent changes
- **Agent team Tech Leads / QA** — want automated regression instead of manual triage
- **Consultants** — standardize Agent evaluation across client projects
- **Learners** — study how production-grade Agent evaluation works

**If you're building a multi-stage Agent and want to evaluate it properly — let's talk.** Open an issue or reach out on Twitter [@IrPVxuhLl557167](https://twitter.com/IrPVxuhLl557167).

---

## Project background

Built while interning at Style3D on a multi-stage AI Agent (vision → brand enrichment → memory → retrieval → PPT generation). Every prompt change meant manual triage — 1-2 days of "did this break anything?" That's not engineering. That's gambling.

After researching LangSmith (too heavy, SaaS-locked), AgentBench (academic, final-result-only), and OpenAI Evals (too generic for multi-step Agents), I designed AgentLens from scratch: a layered evaluation framework inspired by medical imaging (CT scan) and software regression testing (gating mechanism).

The 8-level attribution came from analyzing 91+ real test cases across 4 rounds of iteration — each level maps to a different fix owner, so the report doesn't just say "failed," it says *who needs to fix it*.

Inspired by the [AdaRubric](https://github.com/alphadl/AdaRubrics) paper's task-adaptive rubric scoring concept and Krippendorff's alpha for inter-rater reliability.

---

## Roadmap

- [x] 6-layer evaluation framework (L1-L6)
- [x] 40-item golden test set
- [x] 8-level error attribution waterfall
- [x] xlsx 3-sheet report generation
- [x] `--dry-run` mode (zero config)
- [x] CI pipeline (GitHub Actions)
- [ ] LLM-as-Judge integration for L3 card quality (DeepSeek API)
- [ ] Krippendorff's alpha for LLM-as-Judge reliability
- [ ] Regression diff view (compare two eval runs)
- [ ] Web dashboard for report visualization
- [ ] Community golden set — contribute your domain cases

---

## Architecture

```
AgentLens/
├── src/
│   ├── core/
│   │   ├── models.py          # EvalCase, AgentResponse, LayerScore, EvalResult
│   │   ├── config.py          # YAML/JSON configuration
│   │   ├── pipeline.py        # SixLayerEvaluator orchestrator
│   │   └── report.py          # openpyxl 3-sheet xlsx generation
│   ├── metrics/
│   │   ├── task_completion.py # L1 — did it finish?
│   │   ├── trajectory.py      # L2 — stage graph LCS matching
│   │   ├── card_quality.py    # L3 — rule-based + LLM-as-Judge
│   │   ├── state.py           # L4 — session/brand/asset isolation
│   │   ├── safety.py          # L5 — prompt leak / fallback / PII
│   │   └── stability.py       # L6 — latency / format / reproducibility
│   ├── attribution/
│   │   └── waterfall.py       # 8-level first-match-wins attribution
│   ├── datasets/
│   │   ├── golden_set.py      # 40 adversarial test cases
│   │   └── loader.py           # JSON/YAML dataset loader
│   ├── llm/
│   │   ├── __init__.py         # OpenAI-compatible async client
│   │   └── json_extract.py     # Robust JSON extraction from LLM output
│   └── cli.py                 # --dry-run / --config entry point
├── configs/
│   ├── default.yaml           # Main config
│   ├── rules.yaml             # Attribution rules (editable)
│   └── rubric.yaml            # Layer weights and thresholds
├── tests/                     # 15 tests, all passing
├── examples/                  # Quick start scripts
└── .github/workflows/ci.yml   # CI: lint + test + dry-run smoke
```

---

## License

MIT — see [LICENSE](./LICENSE)

## Acknowledgments

- Rubric scoring concept inspired by [AdaRubric](https://github.com/alphadl/AdaRubrics) (Apache-2.0)
- Krippendorff's alpha for LLM-as-Judge reliability (planned)
- Built during internship at Style3D — the 8-level attribution came from real production failures