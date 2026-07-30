# 🧪 Agent Eval Tool

Automated evaluation pipeline for multi-stage AI Agents — built during my internship at Style3D.

## What it does

- **6-layer evaluation framework** covering task completion, trajectory tracking, intermediate outputs, state consistency, security boundaries, and UX stability
- **40-item golden test set** across 5 business scenarios (happy path, ambiguity recognition, brand/memory sensitivity, search governance, state continuity)
- **0-5 Rubric + Blocker gating** mechanism for quality gates
- **8-level automated error attribution** with rules.yaml configuration
- **xlsx report generation** and regression comparison

## Impact

- Reduced single-round manual evaluation from **1-2 days → minutes**
- Completed **60-round regression testing** with **0 failures, 0 fallbacks, 0 prompt leaks**
- Currently used by the team for daily iteration validation

## Tech

`Python` · `LLM-as-Judge` · `YAML` · `openpyxl` · `Agent Workflow`

## Status

This is a sanitized version of the internal tool. Sensitive business logic and company-specific configurations have been removed.
