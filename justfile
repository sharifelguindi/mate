export COMPOSE_FILE := "docker-compose.local.yml"

## Just does not yet manage signals for subprocesses reliably, which can lead to unexpected behavior.
## Exercise caution before expanding its usage in production environments.
## For more information, see https://github.com/casey/just/issues/2473 .


# Default command to list all available commands.
default:
    @just --list

# build: Build python image.
build:
    @echo "Building python image..."
    @docker compose build

# up: Start up containers.
up:
    @echo "Starting up containers..."
    @docker compose up -d --remove-orphans

# down: Stop containers.
down:
    @echo "Stopping containers..."
    @docker compose down

# prune: Remove containers and their volumes.
prune *args:
    @echo "Killing containers and removing volumes..."
    @docker compose down -v {{args}}

# logs: View container logs
logs *args:
    @docker compose logs -f {{args}}

# manage: Executes `manage.py` command.
manage +args:
    @docker compose run --rm django python ./manage.py {{args}}

# mypy: Run type checking with mypy
mypy *args="mate":
    @echo "Running mypy..."
    @docker compose run --rm django mypy {{args}}

# ruff: Run linting with ruff
ruff *args="":
    @echo "Running ruff check..."
    @docker compose run --rm django ruff check {{args}}

# test: Run tests with pytest
test *args:
    @echo "Running tests..."
    @docker compose run --rm django pytest {{args}}

# coverage: Run tests with coverage and generate HTML report
coverage *args:
    @echo "Running tests with coverage..."
    @docker compose run --rm django coverage run -m pytest {{args}}
    @docker compose run --rm django coverage html
    @echo "Coverage report generated in htmlcov/"
    @open htmlcov/index.html

# coverage-report: View coverage HTML report (macOS)
coverage-report:
    @open htmlcov/index.html

# prod-local: Run production-like environment locally
prod-local:
    @echo "Starting production-like environment locally..."
    @COMPOSE_FILE=docker-compose.production.yml docker compose up -d --build

# prod-build: Build production images
prod-build:
    @echo "Building production images..."
    @COMPOSE_FILE=docker-compose.production.yml docker compose build

# prod-up: Start production containers
prod-up:
    @echo "Starting production containers..."
    @COMPOSE_FILE=docker-compose.production.yml docker compose up -d

# prod-down: Stop production containers
prod-down:
    @echo "Stopping production containers..."
    @COMPOSE_FILE=docker-compose.production.yml docker compose down

# prod-logs: View production container logs
prod-logs *args:
    @COMPOSE_FILE=docker-compose.production.yml docker compose logs -f {{args}}

# prod-ps: Show production container status
prod-ps:
    @COMPOSE_FILE=docker-compose.production.yml docker compose ps

# prod-clean: Stop and remove production containers and volumes
prod-clean:
    @echo "Cleaning production containers and volumes..."
    @COMPOSE_FILE=docker-compose.production.yml docker compose down -v

# prod-setup: Setup production environment files from examples
prod-setup:
    @echo "Setting up production environment files..."
    @test -f .envs/.production/.django || cp .envs/.production/.django.example .envs/.production/.django
    @test -f .envs/.production/.postgres || cp .envs/.production/.postgres.example .envs/.production/.postgres
    @echo "Production environment files ready. Please edit them with your settings."
    @echo "Files to configure:"
    @echo "  - .envs/.production/.django"
    @echo "  - .envs/.production/.postgres"

# prod-shell: Open shell in production Django container
prod-shell:
    @COMPOSE_FILE=docker-compose.production.yml docker compose exec django /bin/bash

# prod-manage: Run Django management command in production
prod-manage +args:
    @COMPOSE_FILE=docker-compose.production.yml docker compose run --rm django python manage.py {{args}}

# prod-migrate: Run migrations in production environment
prod-migrate:
    @echo "Running migrations in production environment..."
    @COMPOSE_FILE=docker-compose.production.yml docker compose run --rm django python manage.py migrate

# prod-collectstatic: Collect static files for production
prod-collectstatic:
    @echo "Collecting static files for production..."
    @COMPOSE_FILE=docker-compose.production.yml docker compose run --rm django python manage.py collectstatic --noinput

# pre-deploy: Run all checks and prepare for deployment (no commit)
pre-deploy:
    @echo "🔍 Running pre-deployment checks..."
    @echo ""
    @echo "1. Running pre-commit hooks..."
    @pre-commit run --all-files || (echo "❌ Pre-commit checks failed!" && exit 1)
    @echo "✅ Pre-commit checks passed"
    @echo ""
    @echo "2. Running mypy type checking..."
    @just mypy || (echo "❌ Type checking failed!" && exit 1)
    @echo "✅ Type checking passed"
    @echo ""
    @echo "3. Running ruff linting..."
    @just ruff || (echo "❌ Linting failed!" && exit 1)
    @echo "✅ Linting passed"
    @echo ""
    @echo "4. Running tests..."
    @just test || (echo "❌ Tests failed!" && exit 1)
    @echo "✅ All tests passed"
    @echo ""
    @echo "5. Checking for uncommitted changes..."
    @if git status --porcelain | grep -q .; then \
        echo "⚠️  Uncommitted changes detected:"; \
        git status --short; \
        echo ""; \
        echo "These changes will need to be committed before deployment."; \
    else \
        echo "✅ Working directory clean"; \
    fi
    @echo ""
    @echo "6. Fetching latest from origin..."
    @git fetch origin
    @echo ""
    @echo "🎉 All pre-deployment checks passed!"
    @echo ""
    @echo "Ready for deployment. Run 'just deploy' to commit and push."

# deploy: Deploy with conventional commit type, message, and optional branch
deploy type message branch="dev":
    @echo "🚀 Starting deployment..."
    @echo ""
    @# Validate commit type
    @if ! echo "{{type}}" | grep -qE "^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)$"; then \
        echo "❌ Invalid commit type: {{type}}"; \
        echo ""; \
        echo "Valid types:"; \
        echo "  feat     - New feature"; \
        echo "  fix      - Bug fix"; \
        echo "  docs     - Documentation changes"; \
        echo "  style    - Code style changes (formatting, etc)"; \
        echo "  refactor - Code refactoring"; \
        echo "  test     - Adding or changing tests"; \
        echo "  chore    - Maintenance tasks"; \
        echo "  perf     - Performance improvements"; \
        echo "  ci       - CI/CD changes"; \
        echo "  build    - Build system changes"; \
        echo "  revert   - Revert a previous commit"; \
        echo ""; \
        echo "Example: just deploy feat 'add user login' dev"; \
        exit 1; \
    fi
    @# Check if there are changes to commit
    @if git status --porcelain | grep -q .; then \
        echo "📝 Uncommitted changes detected:"; \
        echo ""; \
        git status --short; \
        echo ""; \
        msg="{{type}}: {{message}}"; \
        echo "📝 Committing: $$msg"; \
        git add -A; \
        git commit -m "$$msg" || (echo "❌ Commit failed!" && exit 1); \
        echo "✅ Changes committed"; \
    else \
        echo "✅ No uncommitted changes"; \
    fi
    @echo ""
    @echo "Pushing to {{branch}} branch..."
    @git push origin HEAD:{{branch}} || (echo "❌ Push failed!" && exit 1)
    @echo ""
    @echo "✅ Deployment to {{branch}} completed!"
    @# Show environment info based on branch
    @if [ "{{branch}}" = "main" ]; then \
        echo "🚀 Production deployment - {{type}}: {{message}}"; \
    elif [ "{{branch}}" = "staging" ]; then \
        echo "🧪 Staging deployment - {{type}}: {{message}}"; \
    else \
        echo "🔧 Development deployment - {{type}}: {{message}}"; \
    fi
    @echo ""
    @echo "📊 Check GitHub Actions for progress:"
    @echo "   https://github.com/your-org/mate/actions"

# deploy-help: Show deployment usage and examples
deploy-help:
    @echo "📚 Deployment Commands with Conventional Commits"
    @echo ""
    @echo "Usage:"
    @echo "  just deploy <type> <message> [branch]"
    @echo ""
    @echo "Examples:"
    @echo "  just deploy feat 'add user authentication' dev"
    @echo "  just deploy fix 'resolve login bug' main"
    @echo "  just deploy test 'add unit tests for auth' staging"
    @echo "  just deploy docs 'update API documentation'"
    @echo "  just deploy chore 'update dependencies'"
    @echo "  just deploy style 'fix formatting issues'"
    @echo "  just deploy refactor 'extract user service'"
    @echo "  just deploy perf 'optimize database queries' main"
    @echo ""
    @echo "Commit Types:"
    @echo "  feat     - New feature"
    @echo "  fix      - Bug fix"
    @echo "  docs     - Documentation only changes"
    @echo "  style    - Code style/formatting (no logic change)"
    @echo "  refactor - Code restructuring (no behavior change)"
    @echo "  test     - Adding or changing tests"
    @echo "  chore    - Maintenance, dependencies, etc"
    @echo "  perf     - Performance improvements"
    @echo "  ci       - CI/CD configuration changes"
    @echo "  build    - Build system or dependencies"
    @echo "  revert   - Revert a previous commit"
    @echo ""
    @echo "Branches:"
    @echo "  dev      - Development environment (default)"
    @echo "  staging  - Staging/testing environment"
    @echo "  main     - Production environment"
