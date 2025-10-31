.PHONY: start stop restart seed clean help

# Docker compose file location
COMPOSE_FILE = infra/docker-compose.yml

# Default target
.DEFAULT_GOAL := help

help:
	@echo "CVS AI SQL Copilot - Startup Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make start      - Start all services (builds if needed, seeds database)"
	@echo "  make stop       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make seed       - Seed the database"
	@echo "  make logs       - View logs from all services"
	@echo "  make clean      - Stop services and remove volumes"
	@echo "  make help       - Show this help message"
	@echo ""

start: check-env check-docker
	@echo "🚀 Starting CVS AI SQL Copilot..."
	@echo ""
	@if ! docker compose -f $(COMPOSE_FILE) ps 2>/dev/null | grep -q "Up"; then \
		echo "Building and starting services..."; \
		docker compose -f $(COMPOSE_FILE) up -d --build || (echo "❌ Failed to start services. Please ensure Docker is running." && exit 1); \
		echo ""; \
		echo "⏳ Waiting for services to be ready..."; \
		sleep 5; \
		echo "🌱 Seeding database..."; \
		docker compose -f $(COMPOSE_FILE) exec -T backend python -m app.seed || echo "⚠️  Seeding failed, but services are running. You can run 'make seed' manually."; \
	else \
		echo "✅ Services are already running!"; \
	fi
	@echo ""
	@echo "✅ System is ready!"
	@echo ""
	@echo "📍 Access points:"
	@echo "   Frontend:  http://localhost:3000"
	@echo "   Backend:   http://localhost:8000"
	@echo "   Health:    http://localhost:8000/healthz"
	@echo ""
	@echo "💡 To view logs: make logs"
	@echo "💡 To stop:      make stop"

stop: check-docker
	@echo "🛑 Stopping services..."
	docker compose -f $(COMPOSE_FILE) down

restart: stop start

seed: check-docker
	@echo "🌱 Seeding database..."
	docker compose -f $(COMPOSE_FILE) exec backend python -m app.seed

logs: check-docker
	docker compose -f $(COMPOSE_FILE) logs -f

clean: check-docker
	@echo "🧹 Cleaning up (stopping services and removing volumes)..."
	docker compose -f $(COMPOSE_FILE) down -v

check-env:
	@if [ ! -f .env ]; then \
		echo "⚠️  No .env file found. Creating from env.example..."; \
		cp infra/env.example .env; \
		echo "✅ Created .env file. Please review and update it if needed."; \
		echo ""; \
	fi

check-docker:
	@if ! docker info > /dev/null 2>&1; then \
		echo "🐳 Docker is not running. Attempting to start..."; \
		echo ""; \
		if command -v colima > /dev/null 2>&1; then \
			echo "Starting Colima..."; \
			colima start || (echo "❌ Failed to start Colima. Please start it manually: colima start" && exit 1); \
			echo "⏳ Waiting for Docker to be ready..."; \
			sleep 3; \
			max_attempts=30; \
			attempt=0; \
			while [ $$attempt -lt $$max_attempts ]; do \
				if docker info > /dev/null 2>&1; then \
					echo "✅ Docker is ready!"; \
					break; \
				fi; \
				attempt=$$((attempt + 1)); \
				sleep 1; \
			done; \
			if ! docker info > /dev/null 2>&1; then \
				echo "❌ Docker did not start in time. Please check Colima manually."; \
				exit 1; \
			fi; \
		else \
			echo "❌ Error: Docker is not running and Colima is not installed."; \
			echo ""; \
			echo "Please start Docker:"; \
			echo "  - Docker Desktop: Open Docker Desktop application"; \
			echo "  - Colima:         Install with 'brew install colima' then run 'colima start'"; \
			echo ""; \
			exit 1; \
		fi; \
	fi

