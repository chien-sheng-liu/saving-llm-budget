# slb — smart LLM budget CLI

`slb` routes your coding tasks to the right AI tool automatically — Claude Code or Codex — based on what the task actually needs. An LLM judges each prompt and picks the most capable and cost-effective option, then hands off to the tool directly.

```
slb do "Refactor the auth module to use JWT"
  → LLM routing...
  ⚡ Claude Code  93% conf
     Architecture-level refactor across multiple files — Claude handles this better.
  → Launching Claude Code...
```

---

## Install

**Option 1 — one-liner (recommended)**

```bash
curl -fsSL https://raw.githubusercontent.com/chien-sheng-liu/saving-llm-budget/main/install.sh | bash
```

**Option 2 — pipx** *(best for CLI tools, stays isolated)*

```bash
pipx install git+https://github.com/chien-sheng-liu/saving-llm-budget.git
```

**Option 3 — pip**

```bash
pip install git+https://github.com/chien-sheng-liu/saving-llm-budget.git
```

**Requirements:** Python 3.11+. Node.js is installed automatically by `slb setup` if missing.

---

## Setup

Run once after installing:

```bash
slb setup
```

This checks your environment and installs any missing tools:

```
  ✓ Node.js   v22.0.0
  ✓ npm       10.5.0
  ○ Claude Code   not installed
  Install Claude Code now? [Y/n]: Y
  ✓ Claude Code installed!
  ○ Codex   not installed
  Install Codex now? [Y/n]: Y
  ✓ Codex installed!
```

Then set your API keys:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # for Claude Code + LLM routing
export OPENAI_API_KEY="sk-proj-..."     # for Codex
```

Add those lines to your `~/.zshrc` or `~/.bashrc` so they persist.

---

## Usage

### `slb do` — the main command

```bash
slb do "your task in plain English"
```

First run asks how you want routing to work — choose once, never asked again:

```
  auto  — LLM decides and dispatches immediately  (recommended)
  ask   — LLM recommends, you confirm before dispatch
```

**Examples:**

```bash
slb do "Fix the null pointer in UserService.java line 42"
# → Codex (clear, targeted bugfix)

slb do "Redesign the authentication module to support OAuth2"
# → Claude Code (architecture, ambiguous scope)

slb do "Add docstrings to all public functions in utils.py"
# → Codex (mechanical, well-defined)

slb do "I'm not sure why the integration tests keep failing"
# → Claude Code (exploratory, ambiguous)

slb do "Refactor the payments module" --repo ./backend
# → Claude Code, running inside ./backend
```

### `slb chat` — API-based chat (no local CLI needed)

Streams responses directly from Claude or OpenAI. Good for questions, explanations, and quick tasks — no file changes.

```bash
slb chat
```

Every message auto-routes to the right model (Haiku / Sonnet / Opus / GPT-4o-mini / GPT-4o) and shows cost per turn.

### Other commands

| Command | What it does |
|---------|-------------|
| `slb setup` | Install Claude Code and Codex CLI |
| `slb do "..."` | Route + dispatch to Claude Code or Codex |
| `slb chat` | Streaming API chat with auto model selection |
| `slb explain` | Show the routing rules |
| `slb estimate "..."` | Estimate complexity and cost without running |
| `--help` | Help for any command |

---

## How routing works

Every `slb do` call makes a small LLM request (Claude Haiku, ~$0.0003) to judge the task:

```
Task → Claude Haiku → { tool: "claude"|"codex", reasoning, confidence }
```

**Claude Code** is chosen for: architecture, refactoring, ambiguous tasks, code review, multi-file changes, deep reasoning.

**Codex** is chosen for: targeted bugfixes, tests, docs, small well-defined changes, cost-sensitive work.

If a tool isn't installed, `slb` offers to install it. If neither is available, it falls back to direct API calls.

---

## Cost tracking

```
  Routing: 312 in / 28 out  ·  $0.00027
  Session routing cost: 3 calls  ·  $0.00081

  Note: tokens used by Claude Code / Codex CLI are billed directly
  to your Anthropic / OpenAI account.
```

`slb chat` tracks every turn (tokens in/out + cost per message + session total).

---

## Uninstall

```bash
pipx uninstall saving-llm-budget   # if installed via pipx
pip uninstall saving-llm-budget    # if installed via pip
rm -rf ~/.saving-llm-budget        # remove saved config
```
