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

# deploy: Commit changes and deploy to production (interactive)
deploy:
    @echo "🚀 Starting production deployment..."
    @echo ""
    @# Check if there are changes to commit
    @if git status --porcelain | grep -q .; then \
        echo "📝 Uncommitted changes detected:"; \
        echo ""; \
        git status --short; \
        echo ""; \
        read -p "Enter commit message (or press Enter for default): " msg; \
        if [ -z "$$msg" ]; then \
            msg="chore: Production deployment $$(date +%Y-%m-%d)"; \
        fi; \
        git add -A; \
        git commit -m "$$msg" || (echo "❌ Commit failed!" && exit 1); \
        echo "✅ Changes committed"; \
    else \
        echo "✅ No uncommitted changes"; \
    fi
    @echo ""
    @read -p "Enter target branch (default: main): " branch; \
    if [ -z "$$branch" ]; then \
        branch="main"; \
    fi; \
    echo "Pushing to $$branch branch..."; \
    git push origin HEAD:$$branch || (echo "❌ Push failed!" && exit 1)
    @echo ""
    @echo "✅ Deployment initiated! Check GitHub Actions for progress:"
    @echo "   https://github.com/your-org/mate/actions"
    @echo ""
    @echo "📊 Monitor deployment:"
    @echo "   aws ecs list-tasks --cluster mate-cluster --service-name mate-demo-django"

# deploy-force: Deploy with specific branch and message (non-interactive)
deploy-force branch="main" message="":
    @echo "🚀 Starting production deployment to {{branch}}..."
    @echo ""
    @# Check if there are changes to commit
    @if git status --porcelain | grep -q .; then \
        if [ -z "{{message}}" ]; then \
            msg="chore: Production deployment $$(date +%Y-%m-%d)"; \
        else \
            msg="{{message}}"; \
        fi; \
        echo "📝 Committing changes: $$msg"; \
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
    @echo "✅ Deployment initiated! Check GitHub Actions for progress:"
    @echo "   https://github.com/your-org/mate/actions"
    @echo ""
    @echo "📊 Monitor deployment:"
    @echo "   aws ecs list-tasks --cluster mate-cluster --service-name mate-demo-django"
