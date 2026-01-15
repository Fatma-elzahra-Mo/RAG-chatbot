.PHONY: help install test lint format docker-build docker-up docker-down docker-logs clean dev-setup ingest

help:
	@echo "Arabic RAG Chatbot - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install       - Install dependencies with uv"
	@echo "  dev-setup     - Setup development environment"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-cov      - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          - Run linters (ruff, black, mypy)"
	@echo "  format        - Format code with black"
	@echo "  type-check    - Run mypy type checking"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-up     - Start all services"
	@echo "  docker-down   - Stop all services"
	@echo "  docker-logs   - View service logs"
	@echo "  docker-dev    - Start services in development mode"
	@echo ""
	@echo "Data:"
	@echo "  ingest        - Ingest sample data"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         - Clean build artifacts"

install:
	@echo "Installing dependencies with uv..."
	uv pip install -e ".[dev]"

dev-setup: install
	@echo "Setting up development environment..."
	@mkdir -p data/raw data/processed data/vectorstore logs
	@cp -n .env.example .env || true
	@echo "✅ Development environment ready!"
	@echo "   Please configure .env file with your API keys"

test:
	@echo "Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

lint:
	@echo "Running linters..."
	ruff check src/ tests/
	black --check src/ tests/
	mypy src/

format:
	@echo "Formatting code..."
	black src/ tests/
	ruff check --fix src/ tests/

type-check:
	@echo "Running type checking..."
	mypy src/

docker-build:
	@echo "Building Docker image..."
	docker-compose build

docker-up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Waiting for services to start..."
	@sleep 10
	@echo "✅ Services started!"
	@echo "   API: http://localhost:8000"
	@echo "   Docs: http://localhost:8000/docs"

docker-down:
	@echo "Stopping all services..."
	docker-compose down

docker-logs:
	@echo "Viewing service logs (Ctrl+C to exit)..."
	docker-compose logs -f

docker-dev:
	@echo "Starting services in development mode..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

ingest:
	@echo "Ingesting sample data..."
	@./scripts/ingest_sample_data.sh

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov/ dist/ build/ .mypy_cache/ .ruff_cache/ 2>/dev/null || true
	@echo "✅ Cleanup complete!"
