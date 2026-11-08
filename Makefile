# Crayonlark developer commands. Everything runs in Docker; no local Python/ImageMagick needed.
COMPOSE := docker compose -f docker-compose.yml -f docker-compose.dev.yml
PY      := $(COMPOSE) run --rm --no-deps worker-heavy

.PHONY: env up down logs ps build test lint typecheck check demo shell psql admin web-check

env:            ## create .env with random secrets
	./scripts/gen-env.sh

build: env
	$(COMPOSE) build

up: env         ## start the whole stack locally
	$(COMPOSE) up -d --build --wait

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

test:           ## python tests (unit + integration) inside the dev image
	$(COMPOSE) run --rm worker-heavy pytest

lint:
	$(PY) ruff check src tests
	$(PY) ruff format --check src tests

typecheck:
	$(PY) mypy

web-check:
	cd web && pnpm lint && pnpm typecheck

check: lint typecheck test web-check

demo: up        ## run the full pipeline on 5 bundled sample images, zero paid API calls
	mkdir -p demo-output
	$(COMPOSE) run --rm worker-heavy crayonlark demo --out /demo-output

admin:          ## create/reset the admin user
	$(COMPOSE) run --rm api crayonlark create-admin

shell:
	$(COMPOSE) run --rm worker-heavy bash

psql:
	$(COMPOSE) exec postgres psql -U crayonlark crayonlark
