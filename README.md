# saving-llm-budget

`saving-llm-budget` is a cost-aware AI coding CLI. Describe any task in plain English and it automatically picks the most cost-effective model — Claude Haiku, Sonnet, Opus, GPT-4o-mini, or GPT-4o — then streams the answer directly in your terminal.

## Why this tool exists

- Model tokens are expensive — the wrong model wastes budget and time.
- Claude and OpenAI models each have different strengths and price points; automatic routing matches task to model.
- Every routing decision is transparent: you see which model was chosen, why, and what it cost.

## Quick start

```bash
git clone https://github.com/chien-sheng-liu/saving-llm-budget.git
cd saving-llm-budget
pip install -e .
slb chat
```

On first run `slb chat` prompts for your API keys. You can also export them beforehand:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-proj-..."
slb chat
```

At least one key is required; the other can be left blank to disable that provider.

## `slb chat` — auto-routing chat

Every message goes through a five-step pipeline:

1. **Classify** — Claude Haiku reads your prompt and extracts task type, scope, clarity, and priority.
2. **Route** — 20 weighted rules pick Claude vs. OpenAI.
3. **Select model** — maps the routing decision to a specific model:

| Task signal | Model selected |
|---|---|
| Simple / clear / cheapest | `claude-haiku-4-5` or `gpt-4o-mini` |
| Balanced / medium complexity | `claude-sonnet-4-6` or `gpt-4o` |
| Architecture / ambiguous / best quality | `claude-opus-4-6` or `gpt-4o` |

4. **Stream** — the response streams character-by-character.
5. **Cost** — tokens used and USD cost are printed after each reply.

### Example session

```
You
> Why does my Redis connection keep dropping in prod?

→ claude-sonnet-4-6  (Claude, 78% confidence)  Debugging connectivity across services
Assistant
Redis connections drop in production for a few common reasons...

512 in / 340 out — $0.0067  (session: $0.0067)
────────────────────────────────────────────────────────
You
> Write a pytest fixture for a mock Redis client

→ gpt-4o-mini  (Codex, 85% confidence)  Clear, small-scope test generation
Assistant
import pytest
from unittest.mock import MagicMock
...

210 in / 180 out — $0.0001  (session: $0.0068)
```

### Chat commands

| Command | Action |
|---|---|
| `/clear` | Clear conversation history |
| `/cost` | Show total spend this session |
| `/model` | Show last model used |
| `/help` | Show help |
| `/exit` | Quit |

## Other commands

| Command | Purpose |
|---|---|
| `slb init` | Create config + first provider profile |
| `slb ask` | Interactive Q&A routing wizard |
| `slb run "..."` | Non-interactive routing with flags |
| `slb estimate "..."` | Complexity / cost / provider summary |
| `slb explain` | Show the scoring rules and weights |
| `slb profile add/list/use/remove` | Manage provider profiles |
| `slb test [path]` | Run pytest with a Rich summary |
| `slb console` | Persistent routing REPL |

`saving-llm-budget` is an alias for `slb`.

## Routing highlights

- **Claude** gains weight on architecture, large refactors, ambiguity, repo-wide scope, long context, and quality-first priority.
- **OpenAI** shines on bugfixes, tests/docs, small scopes, clear tasks, and cheapest priority.
- **Hybrid** activates for feature/refactor tasks where planning with Claude then executing with GPT-4o-mini saves both cost and quality.
- Scores start from baselines, apply rule weights, and incorporate complexity/cost signals from the estimator. The score spread becomes a confidence percentage.

## Architecture

```
CLI (cli.py / chat.py)
  → RoutingService (classify → estimate → route)
    → ScoringEngine (20 weighted rules in router/rules.py)
      → ModelSelector  → ClaudeChatAdapter / OpenAIChatAdapter
```

Key modules:

| Module | Role |
|---|---|
| `router/rules.py` | 20 weighted heuristic routing rules |
| `services/classifier.py` | LLM task classification via Claude Haiku (heuristic fallback) |
| `services/model_selector.py` | Maps routing decision → specific model ID |
| `providers/claude.py` | Streaming Claude adapter |
| `providers/openai_provider.py` | Streaming OpenAI adapter |
| `services/policies.py` | Budget guardrails |

## Roadmap

1. Persist routing decisions and acceptance rates for feedback loops.
2. Enrich repo scanning with language heuristics and affected-file analysis.
3. Expand policy engine for per-team / per-repo guardrails.
4. JSON and CI-friendly output modes.
