.PHONY: help install dev setup clean test lint format docker-up docker-down docker-build logs

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "SlideGenie Monorepo - Available Commands"
	@echo "======================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "$(YELLOW)Installing root dependencies...$(NC)"
	npm install
	@echo "$(YELLOW)Installing backend dependencies...$(NC)"
	cd slidegenie-backend && poetry install
	@echo "$(YELLOW)Installing frontend dependencies...$(NC)"
	cd slidegenie-frontend && npm install

dev: ## Start development servers
	@echo "$(GREEN)Starting development servers...$(NC)"
	npm run dev

setup: ## Complete setup (Docker + migrations + install)
	@echo "$(YELLOW)Starting Docker services...$(NC)"
	npm run docker:up
	@echo "$(YELLOW)Waiting for services to be ready...$(NC)"
	sleep 10
	@echo "$(YELLOW)Running database migrations...$(NC)"
	cd slidegenie-backend && make migrate
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	$(MAKE) install
	@echo "$(GREEN)Setup complete! You can now run 'make dev' to start the application.$(NC)"

clean: ## Clean all build artifacts and dependencies
	@echo "$(RED)Cleaning build artifacts...$(NC)"
	cd slidegenie-backend && make clean
	cd slidegenie-frontend && rm -rf node_modules .next out
	rm -rf node_modules

test: ## Run all tests
	@echo "$(YELLOW)Running backend tests...$(NC)"
	cd slidegenie-backend && make test
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	cd slidegenie-frontend && npm test

lint: ## Run linters
	@echo "$(YELLOW)Linting backend...$(NC)"
	cd slidegenie-backend && make lint
	@echo "$(YELLOW)Linting frontend...$(NC)"
	cd slidegenie-frontend && npm run lint

format: ## Format code
	@echo "$(YELLOW)Formatting backend...$(NC)"
	cd slidegenie-backend && make format
	@echo "$(YELLOW)Formatting frontend...$(NC)"
	cd slidegenie-frontend && npm run format

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-build: ## Build Docker images
	@echo "$(YELLOW)Building Docker images...$(NC)"
	docker-compose build

docker-clean: ## Clean Docker volumes
	@echo "$(RED)Cleaning Docker volumes...$(NC)"
	docker-compose down -v

logs: ## Show logs from all services
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs
	docker-compose logs -f frontend

ps: ## Show running services
	docker-compose ps

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/sh

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh

db-shell: ## Access PostgreSQL shell
	docker-compose exec postgres psql -U slidegenie -d slidegenie

redis-cli: ## Access Redis CLI
	docker-compose exec redis redis-cli

check-ports: ## Check if required ports are available
	@echo "$(YELLOW)Checking port availability...$(NC)"
	@lsof -i :3000 > /dev/null 2>&1 && echo "$(RED)Port 3000 is in use$(NC)" || echo "$(GREEN)Port 3000 is available$(NC)"
	@lsof -i :8000 > /dev/null 2>&1 && echo "$(RED)Port 8000 is in use$(NC)" || echo "$(GREEN)Port 8000 is available$(NC)"
	@lsof -i :5432 > /dev/null 2>&1 && echo "$(RED)Port 5432 is in use$(NC)" || echo "$(GREEN)Port 5432 is available$(NC)"
	@lsof -i :6379 > /dev/null 2>&1 && echo "$(RED)Port 6379 is in use$(NC)" || echo "$(GREEN)Port 6379 is available$(NC)"
	@lsof -i :9000 > /dev/null 2>&1 && echo "$(RED)Port 9000 is in use$(NC)" || echo "$(GREEN)Port 9000 is available$(NC)"

health-check: ## Check health of all services
	@echo "$(YELLOW)Checking service health...$(NC)"
	@curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "$(GREEN)Backend is healthy$(NC)" || echo "$(RED)Backend is not responding$(NC)"
	@curl -s http://localhost:3000 > /dev/null 2>&1 && echo "$(GREEN)Frontend is healthy$(NC)" || echo "$(RED)Frontend is not responding$(NC)"

update-deps: ## Update all dependencies
	@echo "$(YELLOW)Updating backend dependencies...$(NC)"
	cd slidegenie-backend && poetry update
	@echo "$(YELLOW)Updating frontend dependencies...$(NC)"
	cd slidegenie-frontend && npm update
	@echo "$(YELLOW)Updating root dependencies...$(NC)"
	npm update