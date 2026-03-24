# slb — Saving LLM Budget CLI

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

**Step 1 — install tools**

```bash
slb setup
```

Checks your environment and installs missing tools (Node.js, Claude Code, Codex CLI).

**Step 2 — initialise config**

```bash
slb init
```

Walks you through global settings and lets you configure Claude and Codex **separately** — pick API Key or Local CLI for each:

```
Provider authentication
Set up how to connect to Claude and Codex separately.

Configure Claude now? [Y/n]: Y

  Claude — authentication
    1  API Key  (set an environment variable)
    2  Local CLI  (use the installed claude command)
  Choose (1/2) [1]: 1
  Environment variable for the API key [ANTHROPIC_API_KEY]:
  Profile name [claude-api]:
  ✓ Profile 'claude-api' saved (active).

Configure Codex now? [Y/n]: Y

  Codex — authentication
    1  API Key  (set an environment variable)
    2  Local CLI  (use the installed codex command)
  Choose (1/2) [1]: 2
  Command that launches the local CLI [codex]:
  Profile name [codex-local]:
  ✓ Profile 'codex-local' saved.
```

**If you chose API Key mode**, add the variables to your shell config so they persist:

```bash
# ~/.zshrc or ~/.bashrc
export ANTHROPIC_API_KEY="sk-ant-..."   # Claude (API Key mode)
export OPENAI_API_KEY="sk-proj-..."     # Codex  (API Key mode)
```

Then reload: `source ~/.zshrc`

> `slb` reads directly from your shell environment — it does **not** load `.env` files.
> Only set the keys for providers you configured in API Key mode; Local CLI mode requires no keys.

You can update auth settings at any time:

```bash
slb profile add      # add a new profile
slb profile list     # show all profiles
slb profile switch   # change the active profile
```

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
