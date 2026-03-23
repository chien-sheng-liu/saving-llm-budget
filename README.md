# saving-llm-budget

`saving-llm-budget` is a cost-aware CLI that helps you route engineering tasks to Claude Code, Codex, or a hybrid workflow. Describe the work, share your constraints, and the tool returns a recommendation with rationale, budget guardrails, and future-proof hooks for advanced features.

## Why this tool exists
- Model tokens are expensive—picking the wrong provider wastes budget and time.
- Claude and Codex excel at different types of work; a router helps match task-model fit.
- Teams want transparent scoring, maintainable logic, and budget policies that can evolve.

## Quick start
1. **Clone** (or download releases):
   ```bash
   git clone https://github.com/chien-sheng-liu/saving-llm-budget.git
   cd saving-llm-budget
   ```
2. **Prepare a Python 3.11+ environment** using any workflow you prefer.
   - Conda example:
     ```bash
     conda create -n slb python=3.11 -y
     conda activate slb
     ```
   - Reusing an existing venv/pyenv/system interpreter is fine as long as it meets 3.11+.
3. **Install**:
   ```bash
   pip install -e .
   ```
4. (Optional) Run `saving-llm-budget` with no arguments to see a quick refresher on the next steps at any time.

## Configure once
```
saving-llm-budget init
```
The first run records defaults in `~/.saving-llm-budget/config.yaml` *and* walks through a short profile wizard so you can pick Claude vs. Codex and choose API keys or local CLI access. Profiles are optional—you can skip the wizard, answer `No` when prompted, and add them later with `saving-llm-budget profile add`. If the CLI detects `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in your environment, it automatically creates `claude-auto` / `codex-auto` profiles so you can start immediately.
Set API keys via environment variables (no validation yet):
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-openai-..."
```

## Commands
| Command | Purpose |
| --- | --- |
| `saving-llm-budget init` | Capture defaults, budgets, and optionally create a provider profile |
| `saving-llm-budget ask` | Interactive Q&A that ends with a routing panel |
| `saving-llm-budget run "Refactor auth middleware" ...` | Non-interactive CLI with flags |
| `saving-llm-budget estimate "Fix import errors" ...` | Complexity/cost/provider/workflow summary |
| `saving-llm-budget explain` | Present the scoring rules and weights |
| `saving-llm-budget profile add/list/use/remove` | Manage reusable provider profiles |
| `saving-llm-budget test [path]` | Run pytest locally with a Rich summary |
| `saving-llm-budget console` | Stay inside a mini shell to run multiple subcommands |
| `saving-llm-budget` | Show the quick-start banner when run with no arguments |

### Interactive example
```
saving-llm-budget ask
```
Answer prompts about task description, type, scope, clarity, cost priority, long-context needs, automation, optional repo path, and benchmark mode. Output includes provider/workflow, confidence, reasoning, budget status, repo/diff notes, and policy/benchmark hints. If no profile is configured yet, the router asks whether you want to create one on the spot (or you can skip and continue). When a profile exists, you can override it per run with `--profile <name>`, and the CLI offers to execute the task through that provider (API placeholder or local CLI command).

### Non-interactive example
```
saving-llm-budget run "Refactor auth middleware and add tests" \
  --task-type refactor --scope module --clarity somewhat_ambiguous \
  --priority balanced --long-context --repo-path . --benchmark
```

### Quick estimation
```
saving-llm-budget estimate "Fix import errors in frontend" \
  --task-type bugfix --scope few_files --clarity very_clear \
  --priority cheapest --auto-modify --repo-path ./frontend
```

## Profile management
- `saving-llm-budget profile add`: run the same wizard independently to capture Claude/Codex connections (API or local CLI).
- `saving-llm-budget profile list`: view stored profiles and which one is active.
- `saving-llm-budget profile use <name>`: switch the default profile.
- `saving-llm-budget profile remove <name>`: delete stale configurations.

Every `ask`, `run`, or `estimate` command automatically uses the active profile, but you can override with `--profile <name>` for that single invocation.

## Local test runner
`saving-llm-budget test` wraps `python -m pytest` with a Rich summary so you can run suites locally without leaving the CLI. Examples:

```
saving-llm-budget test          # run the whole suite
saving-llm-budget test tests/test_router_engine.py -v
saving-llm-budget test --last-failed
```

Stdout/stderr from pytest are displayed inline and the exit code mirrors pytest, so the command works in scripts or CI as well.

## Provider execution hooks
- When a profile is selected, `ask`/`run`/`estimate` will offer to execute the task via that provider immediately.
- **API mode**: For now the CLI prints a detailed placeholder (required env vars + task context) so you can copy/paste into your workflow. Future releases can plug in actual API calls.
- **CLI mode**: The stored command (e.g., `claude` or `codex`) is launched with task metadata piped through STDIN, so your local tools can consume it however they want.
- Skip the execution prompt anytime by answering “n”, or run `saving-llm-budget profile add` later to change how tasks are executed.

## Routing highlights
- **Claude** gains weight on architecture, large refactors, ambiguity, repo-wide scopes, quality-first priorities, and long context needs.
- **Codex** shines on bugfixes, tests/docs, small scopes, crystal-clear tasks, automation-friendly workflows, and cheapest priorities.
- **Hybrid** activates when hybrid mode is allowed, profiles support both providers, tasks are feature/refactor-class, scope is module/repo, and planning before execution makes sense.
- Scores start from baselines, apply rule weights, incorporate estimator signals (complexity, token pressure, cost level), and respect config toggles. The spread becomes a confidence metric.
- Available workflows: `direct_claude`, `direct_codex`, `plan_with_claude_then_execute_with_codex`, `codex_then_claude_review`.

## Architecture & future hooks
- `saving_llm_budget.providers`: shared adapter interface so real Claude/OpenAI integrations can plug in later.
- `saving_llm_budget.analysis`: repo scanner + diff analyzer stubs to expand into real repo context and git diff insights.
- `saving_llm_budget.services.policies`: central guardrails for estimated spend and forthcoming team policies.
- `saving_llm_budget.services.context`: aggregates repo/diff/budget/policy/benchmark signals before routing, keeping the engine simple.
- `saving_llm_budget.services.benchmark`: activated via `--benchmark` or the interactive toggle, ready for real benchmark/latency comparisons.
- CLI already accepts repo paths and benchmark flags, so advanced features can land without breaking UX.
- Profile objects capture whether you connect via API keys or vendor CLIs, so additional connection strategies can plug in without touching routing logic.

## Roadmap
1. Wire up actual Claude/OpenAI adapters with token/billing tracking.
2. Persist past routing decisions and acceptance rates for feedback loops.
3. Enrich repo scanning with language heuristics, module complexity, and affected files.
4. Expand policy engine for per-team/per-repo guardrails.
5. Offer JSON and CI-friendly output modes for pipelines.
