# MATE Healthcare Platform

Multi-tenant AI-powered healthcare platform with complete AWS infrastructure isolation for HIPAA compliance.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![AWS](https://img.shields.io/badge/AWS-ECS%20Fargate-FF9900?logo=amazon-aws)](https://aws.amazon.com/ecs/)
[![HIPAA](https://img.shields.io/badge/HIPAA-Compliant-green)](https://aws.amazon.com/compliance/hipaa-compliance/)

## 🛠️ Technology Stack

### Backend
- **Django 5.0** - Web framework
- **PostgreSQL 15** - Primary database
- **Redis 7** - Caching and Celery broker
- **Celery** - Async task processing
- **Django REST Framework** - API development

### Frontend
- **Vite** - Frontend build tool
- **React** - UI framework (optional)
- **Tailwind CSS** - Styling

### AWS Infrastructure (Production)
- **ECS Fargate** - Serverless container hosting
- **RDS PostgreSQL** - Managed database
- **ElastiCache Redis** - Managed cache
- **S3** - Object storage
- **CloudFront** - CDN
- **Cognito** - Authentication & SSO
- **CloudWatch** - Monitoring & logging
- **Terraform** - Infrastructure as Code

## 🚀 Deployment Options

### Production Deployment on AWS
For production deployment using AWS ECS with complete infrastructure isolation:
- 📖 **[Complete Documentation](./documentation/)** - All deployment and operations documentation
- 🚀 **[Quick Start: AWS Setup](./documentation/aws/01-initial-setup.md)** - Initial AWS infrastructure setup
- 📋 **[Operations Guide](./documentation/aws/02-deployment-guide.md)** - Daily operations and tenant management

### Local Development
For local development using Docker Compose, continue reading below.

## Prerequisites for Local Development

- Docker and Docker Compose
- [just](https://github.com/casey/just) command runner (see installation below)
- Git

**Note**: Python, Node.js, and all project dependencies (like ruff, mypy, pytest) are included in the Docker containers. You don't need to install them locally unless you want to develop outside of Docker.

### Installing `just`

`just` is a command runner that makes it easy to run project tasks.

**macOS** (using Homebrew):
```bash
brew install just
```

**Windows** (using Scoop):
```bash
scoop install just
```

**Windows** (using Chocolatey):
```bash
choco install just
```

**Alternative for all platforms** (using cargo):
```bash
cargo install just
```

For more installation options, see the [official just documentation](https://github.com/casey/just#installation).

## Quick Start

### 🌐 For Production AWS Deployment
See [AWS Setup Guide](./documentation/aws/01-initial-setup.md) for complete production deployment instructions.

### 💻 For Local Development

### Project Structure
```
mate/
├── infrastructure/          # AWS Infrastructure
│   └── terraform/          # Terraform modules for AWS
│       ├── modules/        # Reusable infrastructure modules
│       │   ├── tenant/     # Per-tenant resources
│       │   ├── vpc/        # Network configuration
│       │   ├── ecs_cluster/# Container orchestration
│       │   └── cognito/    # Authentication setup
│       └── tenants/        # Tenant configurations
├── mate/                   # Django application
│   ├── tenants/           # Multi-tenant management
│   ├── users/             # User authentication
│   └── provisioning/      # Tenant provisioning
├── frontend/              # Vite/React frontend
├── scripts/               # Deployment scripts
│   ├── deploy.sh          # Main deployment script
│   └── provision-tenant.sh# Tenant provisioning
├── compose/               # Docker configurations
├── documentation/         # Deployment & operations docs
│   └── aws/              # AWS-specific guides
└── docs/                  # Sphinx/ReadTheDocs (API docs)
```

#### 1. Clone the Repository

```bash
git clone https://github.com/your-org/mate.git
cd mate
```

#### 2. Set Up Environment Variables

For local development, copy the existing `.envs/.local/` files (already configured):

```bash
# The .envs/.local/.django and .envs/.local/.postgres files are already set up
# No action needed unless you want to customize them
```

For production deployment on AWS:
- See [AWS Setup Guide](./documentation/aws/01-initial-setup.md) for complete instructions
- Environment variables are managed through AWS Secrets Manager and ECS task definitions

#### 3. Build and Start the Development Environment

```bash
# Build the Docker images
just build

# Start all services (Django, PostgreSQL, Redis, Mailpit, Vite)
just up

# View logs
just logs

# Or view logs for specific service
just logs django
```

#### 4. Initialize the Database

```bash
# Run migrations
just manage migrate

# Create a superuser
just manage createsuperuser
```

#### 5. Frontend Setup (Vite)

The frontend development server starts automatically with `just up`. 

- Frontend files are in the `frontend/` directory
- Vite provides hot module replacement (instant updates)
- **You access everything through Django at http://localhost:8000**
- Django automatically serves Vite's assets in development

## Development Workflow

### Available Commands

All commands are run through `just`. To see all available commands:

```bash
just --list
```

| Command | Description |
|---------|-------------|
| `just build` | Build Docker images |
| `just up` | Start all containers |
| `just down` | Stop all containers |
| `just logs [service]` | View container logs |
| `just manage <command>` | Run Django management commands |
| `just test [args]` | Run tests with pytest |
| `just mypy [path]` | Run type checking |
| `just ruff [args]` | Run linting with ruff |
| `just coverage [args]` | Run tests with coverage report |
| `just prune` | Remove containers and volumes |

### Running Tests

```bash
# Run all tests
just test

# Run specific test file
just test mate/users/tests/test_views.py

# Run with coverage
just coverage

# View coverage report (macOS)
just coverage-report
```

### Code Quality

```bash
# Run linting
just ruff

# Auto-fix linting issues
just ruff --fix

# Type checking
just mypy
```

### Django Management Commands

```bash
# Make migrations
just manage makemigrations

# Apply migrations
just manage migrate

# Create superuser
just manage createsuperuser

# Django shell
just manage shell
```

## Access Points

Once everything is running:

- **Django Application**: http://localhost:8000 (main site)
- **Django Admin**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/
- **Mailpit (Email)**: http://localhost:8025

**Note about Vite**: The Vite dev server runs on port 3000 but you don't access it directly. Django serves the application at http://localhost:8000 and automatically proxies frontend assets from Vite during development. Just use http://localhost:8000 for all your testing.

## User Management

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

## Troubleshooting

### Common Issues

1. **Port already in use**: Stop any services using ports 8000, 3000, 5432, 6379, 8025
2. **Database connection errors**: Ensure PostgreSQL container is running with `just logs postgres`
3. **Frontend assets not loading**: Check Vite container logs with `just logs vite` - you should see assets being served
4. **Vite connection errors**: Make sure you're accessing the site at http://localhost:8000 (NOT :3000)
5. **Permission errors**: Ensure Docker has proper permissions on your system

### Useful Debug Commands

```bash
# Check which containers are running
docker ps

# View specific service logs
just logs django
just logs postgres
just logs vite

# Restart everything
just down
just up

# Complete reset (WARNING: deletes database)
just prune
just build
just up
```

### Frontend Development

The project uses Vite for frontend development with hot module replacement:

- **Access through Django**: http://localhost:8000 (not Vite's port)
- **Auto-reload**: Changes to JS/CSS files are instantly reflected
- **Django Integration**: Use `{% vite_asset %}` tags in templates
- Frontend files are in the `frontend/` directory
- Vite runs in the background on port 3000 but Django proxies everything

### Celery

Celery workers are automatically started when you run `just up`. To run Celery commands manually:

```bash
# Run inside the Django container
just manage celery -A config.celery_app worker -l info

# For periodic tasks
just manage celery -A config.celery_app beat
```

### Email Server

[Mailpit](https://github.com/axllent/mailpit) provides a local SMTP server with web interface for development.

- **Web Interface**: http://localhost:8025
- **SMTP Server**: localhost:1025
- Starts automatically with `just up`

All emails sent by the application in development will appear in Mailpit

### Error Logging

For local development, errors are logged to the console. Check your terminal output for Django errors and debugging information:

```bash
# View Django logs
just logs django

# View all logs
just logs
```

## 🏗️ Multi-Tenant Architecture

MATE uses **AWS-native multi-tenant architecture** with complete infrastructure isolation:

### Each Hospital/Clinic Gets:
- **Dedicated AWS Resources**:
  - Separate ECS services (Django, Celery, Beat)
  - Isolated RDS PostgreSQL database
  - Isolated ElastiCache Redis cluster
  - Dedicated S3 bucket with encryption
  - Custom subdomain (hospital-a.mate.com)
  - Separate CloudWatch logs and metrics

### Infrastructure Tiers:
- **Enterprise**: Multi-AZ RDS, Redis cluster, auto-scaling (2-10 instances)
- **Standard**: Single RDS/Redis, auto-scaling (1-5 instances)
- **Trial**: Shared resources, fixed single instance

### Security & Compliance:
- **HIPAA Compliant**: Full audit trails, encryption at rest/transit
- **Complete Isolation**: No shared databases or storage
- **SSO Support**: Integration with hospital's Azure AD/Okta/SAML
- **AWS Native**: Leverages AWS security best practices

## 🚀 AWS Production Features

When deployed on AWS, MATE provides:

### Infrastructure as Code
- **Terraform Modules**: Complete infrastructure defined in code
- **Automated Provisioning**: One-command tenant deployment
- **GitOps Ready**: CI/CD pipelines for automated deployments

### High Availability
- **Multi-AZ Deployments**: Database and services across availability zones
- **Auto-scaling**: Automatic scaling based on load
- **Load Balancing**: AWS ALB with health checks
- **Zero-downtime Deployments**: Blue-green deployments with ECS

### Monitoring & Operations
- **CloudWatch Integration**: Centralized logging and metrics
- **Cost Tracking**: Per-tenant cost allocation
- **Automated Backups**: Daily RDS snapshots with point-in-time recovery
- **Disaster Recovery**: Infrastructure can be recreated from code

### Tenant Management
```bash
# Provision new tenant
./scripts/provision-tenant.sh

# Deploy updates
./scripts/deploy.sh tenant hospital-a

# Scale services
terraform apply -var-file="tenants/hospital-a.tfvars"
```

For detailed AWS deployment instructions, see:
- [Complete Documentation](./documentation/)
- [AWS Setup Guide](./documentation/aws/01-initial-setup.md)
- [Operations Guide](./documentation/aws/02-deployment-guide.md)

## Contributing

### Code Style

This project uses `ruff` for linting and code formatting. Before committing:

```bash
# Check for linting issues
just ruff

# Auto-fix issues where possible
just ruff --fix

# Run type checking
just mypy
```

### Git Workflow

1. Create a feature branch from `dev`
2. Make your changes
3. Run tests and linting
4. Commit with clear, descriptive messages
5. Push and create a pull request

### Pre-commit Checklist

- [ ] Tests pass: `just test`
- [ ] Linting passes: `just ruff`
- [ ] Type checking passes: `just mypy`
- [ ] Migrations are created if needed: `just manage makemigrations`
- [ ] Documentation is updated if needed

