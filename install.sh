#!/usr/bin/env bash
# slb installer — installs the saving-llm-budget CLI
# Usage: curl -fsSL https://raw.githubusercontent.com/chien-sheng-liu/saving-llm-budget/main/install.sh | bash

set -e

REPO_URL="https://github.com/chien-sheng-liu/saving-llm-budget"
MIN_PYTHON="3.11"

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}  →${RESET} $*"; }
success() { echo -e "${GREEN}  ✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}  ⚠${RESET} $*"; }
error()   { echo -e "${RED}  ✗${RESET} $*"; exit 1; }

# ── banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  slb — smart LLM budget CLI${RESET}"
echo -e "  ${CYAN}${REPO_URL}${RESET}"
echo ""

# ── check Python ──────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    ver=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  error "Python ${MIN_PYTHON}+ is required but not found.
  Install it from: https://www.python.org/downloads/
  Or via Homebrew (macOS):  brew install python@3.12
  Or via apt (Linux):       sudo apt install python3.12"
fi

success "Python $($PYTHON --version | cut -d' ' -f2)"

# ── install ───────────────────────────────────────────────────────────────────
echo ""
info "Installing slb..."

# Prefer pipx (cleaner for CLI tools), fall back to pip
if command -v pipx &>/dev/null; then
  info "Using pipx (isolated install)"
  pipx install "git+${REPO_URL}.git" --force
  success "slb installed via pipx"
else
  info "pipx not found — using pip"
  info "Tip: pipx gives cleaner installs for CLI tools (pip install pipx)"
  "$PYTHON" -m pip install --user "git+${REPO_URL}.git" --quiet
  success "slb installed via pip"

  # Make sure ~/.local/bin is on PATH
  LOCAL_BIN="$HOME/.local/bin"
  if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    warn "Add this to your shell profile (~/.zshrc or ~/.bashrc):"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
  fi
fi

# ── verify ────────────────────────────────────────────────────────────────────
echo ""
if command -v slb &>/dev/null; then
  success "slb $(slb --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo 'installed')"
else
  warn "slb not found in PATH yet. You may need to restart your terminal."
fi

# ── next steps ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Next steps${RESET}"
echo ""
echo -e "  ${CYAN}slb setup${RESET}            Install Claude Code & Codex CLI"
echo -e "  ${CYAN}slb do \"your task\"${RESET}   Route and run your first task"
echo ""
