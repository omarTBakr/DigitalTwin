# DigitalTwin — everything needed to run the ETL DAG (ZenML pipeline `digital_data_etl`).
#
# First time:   make setup          (deps, .env, MongoDB, ZenML repo + local dashboard)
# Every run:    make etl            (brings services up, validates config, runs the pipeline)
# Variants:     make etl USER_ID=omar                                       one user's subscriptions
#               make etl SOURCE_IDS="medium:tag:rag github:user:omartbakr"  exactly these sources
#               make etl-fast       (skip service start + validation; services must already be up)
#
# The repo path contains spaces, so recipes only use relative paths.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

UV      ?= uv
RUN     := $(UV) run
PY      := $(RUN) python

# ---- MongoDB (raw data store; the app itself reads its settings from .env) --
MONGO_CONTAINER ?= digital-twin-mongo
MONGO_IMAGE     ?= mongo:8.2
MONGO_VOLUME    ?= digital_twin_mongo
MONGO_DATABASE  ?= digital_twin
MONGO_PORT      ?= 27017
# localhost only: the database has no auth
MONGO_BIND      ?= 127.0.0.1

# ---- ZenML local server (dashboard) ---------------------------------------
ZENML_PORT      ?= 8237
ZENML_URL       := http://127.0.0.1:$(ZENML_PORT)

# ---- Pipeline selection: the same names as digital_data_etl(user_id, source_ids) --
USER_ID    ?=
SOURCE_IDS ?=
ETL_ARGS   := --etl $(if $(USER_ID),--user $(USER_ID)) $(foreach s,$(SOURCE_IDS),--source $(s))
USER_ARG   := $(if $(USER_ID),--user $(USER_ID))

# USER is the login name the shell always exports, so it can't select a twin user. Catch the
# likely typo `make etl USER=omar` instead of silently running every source.
ifeq ($(origin USER),command line)
$(error USER is your shell login name; use USER_ID=<user id> to pick a twin user)
endif

.PHONY: help setup install env linkedin-sample \
        up down status mongo-up mongo-down mongo-status mongo-shell \
        zenml-init zenml-up zenml-down zenml-status dashboard \
        validate validate-online etl etl-fast \
        dvc-status dvc-push dvc-pull \
        docs-check docs-links \
        lint format clean

help: ## List targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ============================================================================
# One-time setup
# ============================================================================

setup: install env up ## First-time setup: deps, .env, MongoDB, ZenML

install: ## Install Python dependencies into .venv (uv sync)
	$(UV) sync

env: ## Create .env from .env.example if it does not exist
	@if [ -f .env ]; then echo ".env already exists (left unchanged)"; \
	else cp .env.example .env && echo "created .env from .env.example; review it"; fi

linkedin-sample: ## Write a synthetic LinkedIn export (5 articles, 10 posts) until the real one arrives
	$(PY) -m tools.linkedin_sample

# ============================================================================
# Services
# ============================================================================

up: mongo-up zenml-init zenml-up ## Start MongoDB and the ZenML server

down: zenml-down mongo-down ## Stop the ZenML server and MongoDB (data is kept)

status: mongo-status zenml-status ## Show the state of MongoDB and ZenML

mongo-up: ## Start the MongoDB container (creates it on first use) and wait until it answers
	@if docker container inspect $(MONGO_CONTAINER) >/dev/null 2>&1; then \
		docker start $(MONGO_CONTAINER) >/dev/null; \
	else \
		docker run -d --name $(MONGO_CONTAINER) \
			-p $(MONGO_BIND):$(MONGO_PORT):27017 \
			-v $(MONGO_VOLUME):/data/db \
			--restart unless-stopped $(MONGO_IMAGE) >/dev/null; \
	fi
	@echo -n "waiting for MongoDB"; \
	for i in $$(seq 1 30); do \
		if docker exec $(MONGO_CONTAINER) mongosh --quiet --eval 'db.runCommand({ping: 1}).ok' 2>/dev/null | grep -q 1; then \
			echo " ok"; exit 0; fi; \
		echo -n "."; sleep 1; \
	done; echo " timed out"; exit 1

mongo-down: ## Stop the MongoDB container (the volume keeps the data)
	-docker stop $(MONGO_CONTAINER) >/dev/null && echo "MongoDB stopped"

mongo-status: ## Container state and document counts per collection
	@docker ps -a --filter name=^$(MONGO_CONTAINER)$$ --format '{{.Names}}  {{.Status}}  {{.Ports}}'
	@docker exec $(MONGO_CONTAINER) mongosh $(MONGO_DATABASE) --quiet --eval \
		'db.getCollectionNames().sort().forEach(c => print(c.padEnd(16), db[c].countDocuments()))' 2>/dev/null \
		|| echo "MongoDB is not running"

mongo-shell: ## Open mongosh on the twin database
	docker exec -it $(MONGO_CONTAINER) mongosh $(MONGO_DATABASE)

zenml-init: ## Initialise the ZenML repository (.zen/) once
	@if [ -d .zen ]; then echo "ZenML repository already initialised"; else $(RUN) zenml init; fi

zenml-up: ## Start the local ZenML server (dashboard) in the background
	@if curl -sf $(ZENML_URL)/health >/dev/null 2>&1; then echo "ZenML server already running at $(ZENML_URL)"; \
	else $(RUN) zenml login --local --port $(ZENML_PORT); fi

zenml-down: ## Stop the local ZenML server
	-$(RUN) zenml logout --local

zenml-status: ## Show the ZenML client/server status
	@$(RUN) zenml status

dashboard: ## Open the ZenML dashboard in the browser
	xdg-open $(ZENML_URL) >/dev/null 2>&1 &

# ============================================================================
# The ETL workflow
# ============================================================================

validate: ## Validate configs offline: YAML, topics, source specs, local files (USER_ID=)
	$(PY) -m tools.validate_sources --offline $(USER_ARG)

validate-online: ## Validate plus a network health check of each provider (USER_ID=)
	$(PY) -m tools.validate_sources $(USER_ARG)

etl: up validate ## Full workflow: services up, validate, run the ETL pipeline (USER_ID=, SOURCE_IDS=)
	$(PY) -m tools.run $(ETL_ARGS)
	@echo "run finished; see $(ZENML_URL) (make dashboard)"

etl-fast: ## Run the ETL pipeline only; services must be up (USER_ID=, SOURCE_IDS=)
	$(PY) -m tools.run $(ETL_ARGS)

# ============================================================================
# Data versioning (the pipeline's last steps already snapshot and push data/raw)
# ============================================================================

dvc-status: ## Show whether data/raw differs from the last DVC snapshot
	$(RUN) dvc status

dvc-push: ## Push the current data/raw snapshot to the DVC remote
	$(RUN) dvc push

dvc-pull: ## Restore data/raw from the DVC remote
	$(RUN) dvc pull

# ============================================================================
# Software engineering docs (software_engineering/)
# ============================================================================

docs-check: ## Check the design docs: links, every Mermaid diagram renders, story/requirement traceability
	$(PY) -m tools.docs_check

docs-links: ## Same without rendering diagrams (fast, no Node.js needed)
	$(PY) -m tools.docs_check --no-render

# ============================================================================
# Housekeeping
# ============================================================================

lint: ## Ruff lint
	$(RUN) ruff check .

format: ## Ruff format
	$(RUN) ruff format .

clean: ## Remove Python caches
	find . -path ./.venv -prune -o \( -name __pycache__ -o -name .ruff_cache -o -name .mypy_cache \) -type d -print0 | xargs -0 rm -rf
