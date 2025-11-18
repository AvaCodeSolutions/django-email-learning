.PHONY: help install build clean test prebuild postbuild dev-install frontend lint format check

# Default target
help:
	@echo "Django Email Learning - Available commands:"
	@echo ""
	@echo "  install          Install production dependencies"
	@echo "  dev-install      Install development dependencies"
	@echo "  build-backend    Build the backend project with pre/post hooks"
	@echo "  test             Run tests with coverage"
	@echo "  prebuild         Run pre-build script only"
	@echo "  postbuild        Run post-build script only"
	@echo "  build-frontend   Build frontend assets"
	@echo "  lint             Run all linting checks"
	@echo "  format           Format code with ruff"
	@echo "  django-check     Run Django system checks"
	@echo "  migrate          Run database migrations"
	@echo "  runserver        Start development server"
	@echo "  frontend-dev     Start frontend development server"
	@echo "  start-dev        Start both frontend and backend development servers (use with -j)"
	@echo "  dev-init         Setup development environment"
	@echo "  build            Create build (production-ready)"
	@echo ""

# Install production dependencies
install:
	poetry install --only main

# Install development dependencies
dev-install:
	poetry install --with dev
	poetry run pre-commit install

# Run pre-build script
prebuild:
	poetry run python scripts/build.py --prebuild

# Run post-build script
postbuild-cleanup:
	git stash push django_email_learning/templates && git stash drop || true
	rm -rf django_email_learning/static/assets

# Build frontend assets
build-frontend:
	@echo "🎨 Building frontend assets..."
	cd frontend && npm ci && npm run build

# Build backend project with pre/post hooks
build-backend:
	@echo "⚠️  Uncommitted changes in the templates might be overwritten during the build process."
	$(MAKE) prebuild
	cp -r dist/assets django_email_learning/static
	@echo "🏗️  Building backend project..."
	poetry build
	$(MAKE) postbuild-cleanup
	@echo "🎉 Backend build completed successfully!"

# Run tests with coverage
test:
	poetry run pytest --cov=django_email_learning --cov-report=term-missing --cov-report=html

# Run all linting checks
lint:
	@echo "🔍 Running linting checks..."
	poetry run ruff check .
	poetry run mypy .
	poetry run bandit -r django_email_learning/ -f json || true

# Run pre-commit hooks only
pre-commit:
	poetry run pre-commit run --all-files

# Format code
format:
	poetry run ruff format .
	poetry run ruff check --fix .

# Run Django system checks
django-check:
	poetry run python manage.py check

# Run database migrations
migrate:
	poetry run python manage.py migrate

# Start development server
runserver:
	poetry run python manage.py runserver

# Start frontend development server
fronend-dev:
	 cd frontend && npm run dev

# Start both frontend and backend development servers should be used with -j
start-dev: fronend-dev runserver

# Development workflow - install deps and setup
dev-init: dev-install migrate
	@echo "🔧 Development environment ready!"
	@echo "Run 'make runserver' to start the development server"
	@echo "Run 'make frontend-dev' to start Vite dev server in a seperate terminal"
	@echo "Alternatively, you can run 'make -j start-dev' to start both servers concurrently in one terminal"

# Release build (production-ready)
build: build-frontend build-backend
	@echo "📦 Build completed!"
	@echo "Built packages are in dist/"
