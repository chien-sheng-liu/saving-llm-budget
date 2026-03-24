# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`saving-llm-budget` is a cost-aware CLI tool that routes engineering tasks to Claude or Codex (OpenAI) by analyzing task characteristics and recommending the most cost-effective provider. It uses weighted heuristic rules plus optional LLM-powered classification via Claude Haiku.

## Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run CLI
saving-llm-budget --help
saving-llm-budget init
saving-llm-budget ask
saving-llm-budget run --task-type bugfix --scope few_files --clarity clear
saving-llm-budget estimate
saving-llm-budget explain
saving-llm-budget console

# Run tests
pytest
pytest tests/test_router_engine.py   # single test file
pytest -v --last-failed

# Via CLI wrapper
saving-llm-budget test
saving-llm-budget test -v
```

## Architecture

**Layered architecture:**

```
CLI (cli.py)
  → Service Layer (recommender.py, estimator.py, classifier.py, context.py)
    → Router Engine (rules.py, scorer.py, engine.py)
      → Config + Models (config.py, models.py)
        → Providers (base.py, claude.py, codex.py, executor.py)
```

**Routing flow:** `RoutingService` orchestrates Classifier → Estimator → ContextCoordinator → ScoringEngine to produce a `RoutingDecision` with provider recommendation and confidence score.

**Scoring system:** 20 weighted `Rule` tuples in `router/rules.py`. Base scores: Claude=1.5, Codex=1.5, Hybrid=1.0. Rules add/subtract weights. Confidence uses softmax over final scores.

**Key decisions:**
- Claude wins for: architecture, large refactors, ambiguity, long context, quality-first
- Codex wins for: bugfixes, tests/docs, small scopes, clear tasks, cost-sensitive work
- Hybrid: plan with Claude, execute with Codex

## Key Files

| File | Role |
|------|------|
| `src/saving_llm_budget/cli.py` | All CLI subcommands (1300+ lines, Typer) |
| `src/saving_llm_budget/router/rules.py` | 20 weighted heuristic routing rules |
| `src/saving_llm_budget/router/scorer.py` | ScoringEngine applies rules, picks winner |
| `src/saving_llm_budget/services/classifier.py` | LLM task classification (Haiku), with heuristic fallback |
| `src/saving_llm_budget/services/recommender.py` | RoutingService orchestrator |
| `src/saving_llm_budget/providers/base.py` | ProviderAdapter ABC (plan/execute interface) |
| `src/saving_llm_budget/providers/executor.py` | Dispatches tasks to provider adapters |
| `src/saving_llm_budget/repl.py` | Interactive REPL session (prompt_toolkit) |
| `src/saving_llm_budget/models.py` | All Pydantic data models and enums |
| `src/saving_llm_budget/config.py` | YAML config at `~/.saving-llm-budget/config.yaml` |

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...     # Required for LLM classification; falls back to heuristics if absent
OPENAI_API_KEY=sk-proj-...       # Required for Codex API mode
SAVING_LLM_BUDGET_CONFIG_DIR=... # Override config directory (default: ~/.saving-llm-budget)
```

## Provider Adapters

Provider implementations in `providers/claude.py` and `providers/codex.py` are currently stubs returning placeholder results. The `ProviderAdapter` ABC in `providers/base.py` defines the `plan()` → `ProviderPlan` and `execute()` → `ProviderExecutionResult` interface for future real API integration.

## Extending Routing Rules

Add new `Rule` tuples to `router/rules.py`. Each rule is:
```python
Rule(name, provider, description, weight, predicate_fn)
```
where `predicate_fn` receives a `TaskRequest` and returns `bool`.
