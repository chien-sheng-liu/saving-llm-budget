# saving-llm-budget

`saving-llm-budget` is a production-style CLI that routes developer tasks to the best AI coding partner. It compares Claude Code and Codex for each request, scores the options with transparent rules, and returns a recommended workflow that balances cost, fitness, and maintainability.

## Why it exists
- AI coding costs vary wildly; teams need a router that thinks about money first.
- Claude and Codex excel at different jobs. Picking the wrong tool wastes tokens and time.
- Engineers want an auditable decision trail rather than opaque heuristics.

## Installation
```bash
conda create -n saving-llm-budget python=3.11 -y
conda activate saving-llm-budget
pip install -e .
```

## Configuration
Run the init command once per machine:
```bash
saving-llm-budget init
```
This stores answers in `~/.saving-llm-budget/config.yaml`. Example YAML:
```yaml
default_mode: balanced
allow_hybrid: true
max_budget_usd: 40.0
providers:
  claude:
    enabled: true
  codex:
    enabled: true
```
Set API keys outside of git:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-openai-..."
```

## Usage
| Command | Purpose |
| --- | --- |
| `saving-llm-budget init` | Create the local config and document API key usage |
| `saving-llm-budget ask` | Guided Q&A that routes a task interactively |
| `saving-llm-budget run "Refactor auth middleware and add tests"` | Non-interactive recommendation for scripts or aliases |
| `saving-llm-budget estimate "Fix import errors in frontend"` | Get complexity, cost, provider, and workflow |
| `saving-llm-budget explain` | Inspect the weighted routing rules |

### Interactive example
```
saving-llm-budget ask
```
Answer prompts about task type, scope, clarity, long context, automation, optional repo path, and whether to enable benchmark notes. The CLI prints a Rich panel with provider, workflow, confidence, reasoning, estimated cost level, guardrails, and follow-up instructions.

### Non-interactive example
```
saving-llm-budget run "Refactor auth middleware and add tests" --task-type refactor --scope module --clarity somewhat_ambiguous --priority balanced --long-context --repo-path . --benchmark
```

### Quick estimation
```
saving-llm-budget estimate "Fix import errors in frontend" --task-type bugfix --scope few_files --clarity very_clear --priority cheapest --auto-modify --repo-path ./frontend
```

## Routing logic highlights
- **Claude**: rewarded for architecture, large refactors, ambiguous inputs, repo-wide scope, high-quality priority, and long-context needs.
- **Codex**: rewarded for bugfixes, tests/docs, small scopes, crystal-clear requirements, automation, and cost-sensitive work.
- **Hybrid**: enabled when both models are on, the task is a feature or refactor, scope is module/repo, and some ambiguity suggests planning before implementation.
- Scores start from a baseline, add rule weights, factor in estimator output (complexity, cost, token pressure), then convert into a normalized confidence.
- Workflows include `direct_claude`, `direct_codex`, `plan_with_claude_then_execute_with_codex`, and `codex_then_claude_review`.

## Architecture & future hooks
- **Provider adapters** (`saving_llm_budget.providers`) expose a shared protocol so real Claude/Codex integrations can be added without touching the CLI.
- **Analysis layer** (`saving_llm_budget.analysis`) already contains repo scanning and diff analyzers that currently return stubs but establish the extension point for repo context and git diff analysis.
- **Budget & policy services** (`saving_llm_budget.services.policies`) centralize guardrail logic, surfacing estimated spend vs. configured budgets right in the CLI output.
- **Context coordinator** (`saving_llm_budget.services.context`) stitches repo, diff, budget, policy, and benchmark data together before routing, keeping the router itself simple and future-proof.
- **Benchmark service** (`saving_llm_budget.services.benchmark`) is triggered via `--benchmark` or the interactive toggle, ready to plug into real benchmark workflows.
- **CLI inputs** already accept repo paths and benchmark flags so adding repo scanning, git diff analysis, budget enforcement, team policies, or benchmark comparisons will not break the existing UX contract.

## Future roadmap
1. Plug in actual Claude/OpenAI API calls once billing is configured.
2. Surface historical routing decisions and acceptance metrics.
3. Extend estimations with repo stats (files touched, diff size).
4. Add policy hooks so teams can enforce guardrails per repository.
5. Offer JSON output for CI pipelines.
