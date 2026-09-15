.PHONY: install run debug clean lint lint-strict

UV := $(shell command -v uv 2>/dev/null || echo "$(HOME)/.local/bin/uv")

check-uv:
	@if ! command -v uv >/dev/null 2>&1 && [ ! -x "$(UV)" ]; then \
		echo "\033[1;33muv no está instalado. Instalando...\033[0m"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "\033[1;32muv instalado correctamente.\033[0m"; \
	fi

install: check-uv
	@$(UV) sync

RUN_ARGS := $(filter-out run --,$(MAKECMDGOALS))
RUN_ARGS := $(filter-out run, $(MAKECMDGOALS))

run:
# 	@clear
	@$(MAKE) install --no-print-directory
	@echo "\033[1;33m"
	@echo "    _______       ___      _______ "
	@echo "   |   __  \     /   \    |   ____|"
	@echo "   |  |__)  |   / /_\ \   |  |  __ "
	@echo "   |   _   /   /  ___  \  |  | |_ |"
	@echo "   |  | \  \  /  /   \  \ |  \__| |"
	@echo "   |_ |  \__\/__/     \__\|_______|"
	@echo ""
	@echo "        against the machine"
	@echo "\033[0m"
	@echo "\n"
	-@uv run python -m src $(RUN_ARGS)
	@echo "\033[1;31m"
	@echo "\nEND OF PROGRAM - SEE YOU SOON!"
	@echo "\033[0m"
	@$(MAKE) clean --no-print-directory

debug:
	@uv run python -m pdb -m src

clean:
	@rm -rf .mypy_cache .pytest_cache
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -name '*.pyc' -delete

lint:
	@clear
	@uv run flake8 . --exclude=.venv,data,__pycache__
	@uv run mypy . --exclude "(.venv|data)" --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
	@$(MAKE) clean --no-print-directory

lint-strict:
	@clear
	@uv run flake8 . --exclude=.venv,data,__pycache__
	@uv run mypy . --strict --exclude "(.venv|data)"
	@$(MAKE) clean --no-print-directory

%:
	@: