.PHONY: install setup dev run clean help

# Default target
.DEFAULT_GOAL := help

# Install dependencies
install:
	@echo "Installing dependencies..."
	uv sync

# Setup project (install dependencies and any initial setup)
setup: install
	@echo "Project setup complete."

# Run development server
dev:
	@echo "Starting development server..."
	uv run uvicorn app.main:app --reload

# Run production server
run:
	@echo "Starting production server..."
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Clean up pycache and other temporary files
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

# Help command to list available targets
help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies using uv"
	@echo "  make setup    - Setup the project (install dependencies)"
	@echo "  make dev      - Run the development server with reload"
	@echo "  make run      - Run the production server"
	@echo "  make clean    - Remove cache and temporary files"

migrate:
	uv run alembic upgrade head

test:
	uv run pytest tests/
