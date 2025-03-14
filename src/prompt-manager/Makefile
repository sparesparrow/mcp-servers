.PHONY: build run test clean install install-dev

# Variables
DOCKER_IMAGE := prompt-manager:latest
DOCKER_COMPOSE := docker-compose
PYTHON := python3
PIP := pip

# Default target
all: install

# Build the Docker image
build:
	docker build -t $(DOCKER_IMAGE) .

# Run the Docker container
run: build
	docker run --rm -i $(DOCKER_IMAGE)

# Run with Docker Compose
compose-up:
	$(DOCKER_COMPOSE) up -d

# Stop Docker Compose
compose-down:
	$(DOCKER_COMPOSE) down

# Run tests
test:
	$(PYTHON) -m pytest tests/ -v

# Clean up build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Install as a package
install:
	$(PIP) install -e .

# Install in development mode with test dependencies
install-dev:
	$(PIP) install -e ".[dev,test]"

# Add to Claude Desktop configuration
claude-desktop-config:
	@echo "Adding prompt-manager to Claude Desktop configuration..."
	@python -c "import json, os; \
	config_path = os.path.expanduser('~/.config/Claude/claude_desktop_config.json'); \
	config = json.load(open(config_path)) if os.path.exists(config_path) else {'mcpServers': {}}; \
	config['mcpServers']['prompt-manager'] = { \
		'command': 'docker', \
		'args': ['run', '--rm', '-i', '-v', 'mcp-prompt-manager-data:/data', 'prompt-manager:latest'] \
	}; \
	os.makedirs(os.path.dirname(config_path), exist_ok=True); \
	json.dump(config, open(config_path, 'w'), indent=2)"
	@echo "Configuration updated successfully!"

# Help
help:
	@echo "Available targets:"
	@echo "  build            - Build the Docker image"
	@echo "  run              - Run the Docker container"
	@echo "  compose-up       - Start using Docker Compose"
	@echo "  compose-down     - Stop Docker Compose"
	@echo "  test             - Run tests"
	@echo "  clean            - Clean up build artifacts"
	@echo "  install          - Install as a package"
	@echo "  install-dev      - Install in development mode"
	@echo "  claude-desktop-config - Add to Claude Desktop configuration"
	@echo "  help             - Show this help" 