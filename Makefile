PROJECT_DIR := $(shell pwd)
TEST_DIR    := /tmp/slb-playground
CONFIG_DIR  := $(HOME)/.saving-llm-budget
CONFIG_BAK  := $(HOME)/.saving-llm-budget.bak

.PHONY: install test test-unit reset-config playground clean-playground help

# ── Development ───────────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]"

test:
	pytest tests/ --ignore=tests/test_repl.py -q

test-verbose:
	pytest tests/ --ignore=tests/test_repl.py -v

# ── UX / manual testing ───────────────────────────────────────────────────────

## Create a scratch directory with sample files to test `slb do` against
playground:
	@mkdir -p $(TEST_DIR)
	@echo 'def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b' > $(TEST_DIR)/math_utils.py
	@echo 'import math_utils\n\nresult = math_utils.add(1, 2)\nprint(result)' > $(TEST_DIR)/main.py
	@echo "class UserService:\n    def get_user(self, id):\n        pass  # TODO: implement" > $(TEST_DIR)/user_service.py
	@echo ""
	@echo "  Playground ready at: $(TEST_DIR)"
	@echo ""
	@echo "  Try:"
	@echo "    cd $(TEST_DIR) && slb do 'add type hints to math_utils.py'"
	@echo "    cd $(TEST_DIR) && slb do 'implement the get_user method'"
	@echo "    cd $(TEST_DIR) && slb chat"

## Remove playground directory
clean-playground:
	rm -rf $(TEST_DIR)
	@echo "  Playground removed."

## Backup current config and simulate a brand-new user (no config, no keys)
reset-config:
	@if [ -d "$(CONFIG_DIR)" ]; then \
		cp -r $(CONFIG_DIR) $(CONFIG_BAK) && \
		rm -rf $(CONFIG_DIR) && \
		echo "  Config backed up to $(CONFIG_BAK) and cleared."; \
	else \
		echo "  No config found — already clean."; \
	fi
	@echo ""
	@echo "  You are now in a fresh-user state. Test with:"
	@echo "    ANTHROPIC_API_KEY='' OPENAI_API_KEY='' slb chat"
	@echo "    slb setup"
	@echo ""
	@echo "  Restore with: make restore-config"

## Restore config from backup
restore-config:
	@if [ -d "$(CONFIG_BAK)" ]; then \
		rm -rf $(CONFIG_DIR) && \
		mv $(CONFIG_BAK) $(CONFIG_DIR) && \
		echo "  Config restored from backup."; \
	else \
		echo "  No backup found at $(CONFIG_BAK)."; \
	fi

## Full reset: backup config + open playground in a subshell
fresh-start: reset-config playground
	@echo ""
	@echo "  Opening playground shell (type 'exit' to return)..."
	@cd $(TEST_DIR) && ANTHROPIC_API_KEY="" OPENAI_API_KEY="" $$SHELL

## Test in an isolated virtualenv (simulates pip install from scratch)
test-isolated:
	@echo "  Creating isolated virtualenv..."
	@python -m venv /tmp/slb-isolated-env
	@/tmp/slb-isolated-env/bin/pip install -e "$(PROJECT_DIR)" -q
	@echo ""
	@echo "  Virtualenv ready. Run:"
	@echo "    source /tmp/slb-isolated-env/bin/activate"
	@echo "    slb setup"
	@echo "    slb chat"
	@echo ""
	@echo "  Clean up with: make clean-isolated"

clean-isolated:
	rm -rf /tmp/slb-isolated-env
	@echo "  Isolated virtualenv removed."

help:
	@echo ""
	@echo "  slb development commands"
	@echo ""
	@echo "  make install          Install in editable mode"
	@echo "  make test             Run unit tests"
	@echo ""
	@echo "  make playground       Create sample files in /tmp/slb-playground"
	@echo "  make reset-config     Simulate a brand-new user (backs up config)"
	@echo "  make restore-config   Restore config from backup"
	@echo "  make fresh-start      reset-config + playground + open a shell"
	@echo "  make test-isolated    Install in a fresh virtualenv"
	@echo ""
