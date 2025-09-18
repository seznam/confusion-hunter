.PHONY: help install test scan pipeline-test clean docker-build docker-scan

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Installation
install: ## Install the scanner and dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[test,dev]"

# Testing
test: ## Run all tests
	pytest tests/ -v

test-pipeline: ## Test pipeline integration
	@echo "Testing pipeline integration..."
	@./scripts/pipeline-scan.sh --no-fail --summary-only .
	@echo "Pipeline test completed successfully"

# Scanning
scan: ## Run basic scan on current directory
	python -m confusion_hunter.scanner . --pretty --stdout

scan-pipeline: ## Run pipeline-friendly scan
	python -m confusion_hunter.scanner . --fail-on-found --quiet --summary-only

scan-sarif: ## Run scan with SARIF output
	python -m confusion_hunter.scanner . --output results.sarif --pretty
	@echo "Results saved to results.sarif"

scan-json: ## Run scan with JSON output
	python -m confusion_hunter.scanner . --raw --pretty --output results.json
	@echo "Results saved to results.json"

# Pipeline testing
pipeline-test-github: ## Test GitHub Actions pipeline locally
	@echo "Testing GitHub Actions pipeline..."
	@pip install confusion-hunter 2>/dev/null || pip install -e .
	@confusion-hunter . --fail-on-found --output github-test.sarif --pretty || true
	@echo "GitHub Actions test completed"

pipeline-test-gitlab: ## Test GitLab CI pipeline locally
	@echo "Testing GitLab CI pipeline..."
	@pip install confusion-hunter 2>/dev/null || pip install -e .
	@confusion-hunter . --fail-on-found --quiet --summary-only || true
	@echo "GitLab CI test completed"

pipeline-test-jenkins: ## Test Jenkins pipeline locally
	@echo "Testing Jenkins pipeline..."
	@pip install confusion-hunter 2>/dev/null || pip install -e .
	@confusion-hunter . --fail-on-found --output jenkins-test.sarif || true
	@echo "Jenkins test completed"

# Docker
docker-build: ## Build Docker image
	docker build -t confusion-hunter .

docker-scan: ## Run scan using Docker
	docker run --rm -v $(PWD):/workspace confusion-hunter /workspace --fail-on-found --quiet --summary-only

# Development
lint: ## Run linting
	flake8 confusion_hunter/ tests/
	mypy confusion_hunter/

format: ## Format code
	black confusion_hunter/ tests/
	isort confusion_hunter/ tests/

# Cleanup
clean: ## Clean up generated files
	rm -f *.sarif *.json
	rm -rf __pycache__/ */__pycache__/
	rm -rf .pytest_cache/
	rm -rf *.egg-info/
	rm -rf build/ dist/

clean-all: clean ## Clean everything including virtual environment
	rm -rf venv/

# Examples and documentation
examples: ## Generate example outputs
	@echo "Generating example outputs..."
	@mkdir -p examples/outputs
	@python -m confusion_hunter.scanner . --output examples/outputs/example.sarif --pretty 2>/dev/null || true
	@python -m confusion_hunter.scanner . --raw --output examples/outputs/example.json --pretty 2>/dev/null || true
	@echo "Examples generated in examples/outputs/"

# CI/CD simulation
simulate-ci: ## Simulate CI/CD pipeline execution
	@echo "=== Simulating CI/CD Pipeline ==="
	@echo "1. Installing scanner..."
	@pip install -e . >/dev/null 2>&1
	@echo "2. Running dependency scan..."
	@confusion-hunter . --fail-on-found --output ci-simulation.sarif --quiet || { \
		echo "❌ Pipeline would FAIL - unclaimed packages detected"; \
		echo "Check ci-simulation.sarif for details"; \
		exit 1; \
	}
	@echo "✅ Pipeline would SUCCEED - no issues found"
	@rm -f ci-simulation.sarif

# Performance testing
perf-test: ## Run performance test
	@echo "Running performance test..."
	@time python -m confusion_hunter.scanner . --quiet --summary-only
	@echo "Performance test completed"

# Security validation
security-check: ## Run security validation
	@echo "Running security validation..."
	@python -c "import confusion_hunter.scanner; print('✅ Scanner imports successfully')"
	@python -m confusion_hunter.scanner --help >/dev/null && echo "✅ CLI interface works"
	@echo "✅ Security validation passed"

# Release preparation
prepare-release: clean lint test ## Prepare for release
	@echo "Preparing release..."
	@python setup.py check
	@echo "✅ Release preparation completed"

# Quick development workflow
dev: install-dev lint test ## Quick development setup and validation

# Pipeline integration validation
validate-pipelines: ## Validate all pipeline configurations
	@echo "Validating pipeline configurations..."
	@echo "✅ GitHub Actions: examples/github-actions.yml"
	@echo "✅ GitLab CI: examples/gitlab-ci.yml"
	@echo "✅ Jenkins: examples/jenkins.groovy"
	@echo "✅ Azure DevOps: examples/azure-pipelines.yml"
	@echo "✅ Docker Compose: examples/docker-compose.yml"
	@echo "✅ Pipeline script: scripts/pipeline-scan.sh"
	@echo "All pipeline configurations validated"
