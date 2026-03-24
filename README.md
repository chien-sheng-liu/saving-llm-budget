# slb — Saving LLM Budget CLI

`slb` routes your coding tasks to the right AI tool automatically — Claude Code or Codex — based on what the task actually needs. An LLM judges each prompt and picks the most capable and cost-effective option, then hands off to the tool directly.

`slb` stays open like an interactive shell. Every command returns to the `slb>` prompt — you never leave the CLI.

```
$ slb
slb> Refactor the auth module to use JWT

  ⚡ Claude Code  93% conf
     Architecture-level refactor across multiple files — Claude handles this better.
  → Launching Claude Code...

╭─ Back from Claude Code ────────────────────────╮
│ ✓ Done  ·  session time: 3m 42s                │
│ Note: token usage billed to your Anthropic     │
│ account.                                       │
╰────────────────────────────────────────────────╯

  Session routing cost: 1 call · $0.00027

slb> _
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
  Enter the API key directly? [y/N]: y
  API key: ****
  ✓ Profile 'claude-api' saved (active).

Configure Codex now? [Y/n]: Y

  Codex — authentication
    1  API Key  (set an environment variable)
    2  Local CLI  (use the installed codex command)
  Choose (1/2) [1]: 2
  Command that launches the local CLI [codex]:
  ✓ Profile 'codex-local' saved.
```

**API Key mode — two ways to provide the key:**

| Option | How | Where it's stored |
|--------|-----|-------------------|
| Enter directly | Paste when prompted | `~/.saving-llm-budget/config.yaml` (permissions: 600) |
| Environment variable | Point to an env var name | Your shell (`~/.zshrc` or `~/.bashrc`) |

If you choose environment variable, add the keys to your shell config:

```bash
# ~/.zshrc or ~/.bashrc
export ANTHROPIC_API_KEY="sk-ant-..."   # Claude (API Key mode)
export OPENAI_API_KEY="sk-proj-..."     # Codex  (API Key mode)
```

Then reload: `source ~/.zshrc`

> `slb` reads directly from your shell environment — it does **not** load `.env` files.
> Local CLI mode requires no API keys.

You can update auth settings at any time:

```bash
slb profile add      # add a new profile
slb profile list     # show all profiles
slb profile switch   # change the active profile
```

**First run shortcut:** just type `slb` — if no config exists, setup runs automatically before dropping into the interactive prompt.

---

## Usage

`slb` is a persistent CLI. Type `slb` once and stay in the session:

```
slb> your task in plain English
slb> /help
slb> exit
```

Or run individual commands from your shell — each returns to `slb>` when done:

```bash
slb do "your task"
slb chat
slb explain
```

### Routing tasks

Type a task directly at the `slb>` prompt, or use `slb do`:

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

First run asks how you want routing to work — choose once, never asked again:

```
  auto  — LLM decides and dispatches immediately  (recommended)
  ask   — LLM recommends, you confirm before dispatch
```

### `slb chat` — API-based chat (no local CLI needed)

Streams responses directly from Claude or OpenAI. Good for questions, explanations, and quick tasks — no file changes.

Every message auto-routes to the right model (Haiku / Sonnet / Opus / GPT-4o-mini / GPT-4o) and shows cost per turn.

### Other commands

| Command | What it does |
|---------|-------------|
| `slb setup` | Install Claude Code and Codex CLI |
| `slb init` | Configure providers and auth |
| `slb do "..."` | Route + dispatch to Claude Code or Codex |
| `slb chat` | Streaming API chat with auto model selection |
| `slb explain` | Show the routing rules |
| `slb estimate "..."` | Estimate complexity and cost without running |
| `exit` / `Ctrl+C` | Leave the REPL |
| `--help` | Help for any command |

---

## How routing works

Every task makes a small LLM request (Claude Haiku, ~$0.0003) to judge the task:

```
Task → Claude Haiku → { tool: "claude"|"codex", reasoning, confidence }
```

**Claude Code** is chosen for: architecture, refactoring, ambiguous tasks, code review, multi-file changes, deep reasoning.

**Codex** is chosen for: targeted bugfixes, tests, docs, small well-defined changes, cost-sensitive work.

If a tool isn't installed, `slb` offers to install it. If neither is available, it falls back to direct API calls.

---

## Cost tracking

After each Claude Code or Codex session, `slb` shows:

```
╭─ Back from Claude Code ──────────────────╮
│ ✓ Done  ·  session time: 3m 42s          │
│ Note: token usage billed to your         │
│ Anthropic / OpenAI account.              │
╰──────────────────────────────────────────╯

  Session routing cost: 1 call · $0.00027
```

- **Session time** — how long the tool ran
- **Routing cost** — the Haiku classification call (`slb` side)
- **Tool token usage** — billed directly to your Anthropic / OpenAI account (not tracked by `slb`)

`slb chat` tracks every turn (tokens in/out + cost per message + session total).

---

## Uninstall

```bash
pipx uninstall saving-llm-budget   # if installed via pipx
pip uninstall saving-llm-budget    # if installed via pip
rm -rf ~/.saving-llm-budget        # remove saved config
```
