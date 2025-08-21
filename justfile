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
