# ============================================================
# PROPTECH PDE — Makefile
# ============================================================

.PHONY: help up down build logs shell migrate seed scrape test lint backup

# Colors
RED    := \033[31m
GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
RESET  := \033[0m

help: ## Mostrar ayuda
	@echo "$(BLUE)PropTech PDE — Comandos disponibles$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

# ─── DOCKER ─────────────────────────────────────────────────
up: ## Levantar todos los servicios
	@echo "$(GREEN)▶ Levantando servicios...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)✅ Servicios activos$(RESET)"
	@echo "   API:       http://localhost:8000/docs"
	@echo "   Frontend:  http://localhost:3000"
	@echo "   Metabase:  http://localhost:3001"
	@echo "   PGAdmin:   http://localhost:5050"
	@echo "   Flower:    http://localhost:5555"

down: ## Bajar servicios
	@echo "$(YELLOW)▼ Bajando servicios...$(RESET)"
	docker compose down

build: ## Rebuild imágenes Docker
	docker compose build --no-cache

logs: ## Ver logs de todos los servicios
	docker compose logs -f --tail=100

logs-api: ## Ver logs del API
	docker compose logs -f api --tail=200

logs-worker: ## Ver logs del worker
	docker compose logs -f worker --tail=200

restart: ## Reiniciar servicios
	docker compose restart

# ─── DATABASE ───────────────────────────────────────────────
migrate: ## Correr migrations de Alembic
	@echo "$(BLUE)▶ Corriendo migrations...$(RESET)"
	docker compose exec api alembic upgrade head
	@echo "$(GREEN)✅ Migrations completadas$(RESET)"

migrate-create: ## Crear nueva migration (use: make migrate-create MSG="descripcion")
	docker compose exec api alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback última migration
	docker compose exec api alembic downgrade -1

seed: ## Poblar DB con datos iniciales
	@echo "$(BLUE)▶ Insertando seed data...$(RESET)"
	docker compose exec api python -m app.db.seeds
	@echo "$(GREEN)✅ Seed completado$(RESET)"

db-shell: ## Abrir shell de PostgreSQL
	docker compose exec postgres psql -U proptech proptech_pde

# ─── DESARROLLO ─────────────────────────────────────────────
shell-api: ## Shell dentro del container API
	docker compose exec api bash

shell-worker: ## Shell dentro del container Worker
	docker compose exec worker bash

# ─── SCRAPERS ───────────────────────────────────────────────
scrape: ## Correr todos los scrapers
	@echo "$(BLUE)▶ Iniciando scrapers...$(RESET)"
	docker compose exec api python -m app.scrapers.runner --all

scrape-ml: ## Scraper MercadoLibre
	docker compose exec api python -m app.scrapers.runner --source mercadolibre

scrape-infocasas: ## Scraper InfoCasas
	docker compose exec api python -m app.scrapers.runner --source infocasas

scrape-gallito: ## Scraper Gallito Luis
	docker compose exec api python -m app.scrapers.runner --source gallito

# ─── TESTING ────────────────────────────────────────────────
test: ## Ejecutar todos los tests
	@echo "$(BLUE)▶ Ejecutando tests...$(RESET)"
	docker compose exec api pytest tests/ -v --tb=short
	@echo "$(GREEN)✅ Tests completados$(RESET)"

test-unit: ## Solo tests unitarios
	docker compose exec api pytest tests/unit/ -v

test-integration: ## Solo tests de integración
	docker compose exec api pytest tests/integration/ -v

test-cov: ## Tests con coverage
	docker compose exec api pytest tests/ --cov=app --cov-report=html --cov-report=term

# ─── CODE QUALITY ───────────────────────────────────────────
lint: ## Linting y formateo
	docker compose exec api ruff check app/ --fix
	docker compose exec api black app/
	docker compose exec api isort app/
	docker compose exec api mypy app/

format: ## Solo formateo
	docker compose exec api black app/ && docker compose exec api isort app/

# ─── BACKUP ─────────────────────────────────────────────────
backup: ## Backup de base de datos
	@echo "$(BLUE)▶ Creando backup...$(RESET)"
	@mkdir -p backups
	docker compose exec postgres pg_dump -U proptech proptech_pde | gzip > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)✅ Backup creado en backups/$(RESET)"

restore: ## Restaurar backup (use: make restore FILE=backups/xxx.sql.gz)
	gunzip -c $(FILE) | docker compose exec -T postgres psql -U proptech proptech_pde

# ─── PRODUCCIÓN ─────────────────────────────────────────────
prod-up: ## Levantar en modo producción
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# ─── FRONTEND ───────────────────────────────────────────────
frontend-install: ## Instalar dependencias del frontend
	cd frontend && npm install

frontend-dev: ## Correr frontend en desarrollo local
	cd frontend && npm run dev

frontend-build: ## Build del frontend
	docker compose exec frontend npm run build
