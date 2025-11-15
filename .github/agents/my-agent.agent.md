---
# Fill in the fields below to create a basic custom agent for your repository.
# The Copilot CLI can be used for local testing: https://gh.io/customagents/cli
# To make this agent available, merge this file into the default repository branch.
# For format details, see: https://gh.io/customagents/config

name: Django Email Learning Developer Agent
description: Developer agent
---

# Django Email Learning Developer Agent

## Project Overview

**Django Email Learning** is a Django-based platform for creating and delivering educational content via email with IMAP integration and React frontend components. The project enables organizations to manage email-based learning courses with user role management and interactive frontend interfaces.

## Architecture & Technology Stack

### Backend (Django)
- **Django 5.0** - Main web framework
- **Python 3.12+** - Programming language
- **SQLite** - Database (development)
- **Pydantic** - API request/response validation
- **Cryptography** - IMAP password encryption

### Frontend
- **React 19** with **Vite 7** - Frontend framework and build tool
- **Material-UI (MUI)** - React component library
- **Multi-page application (MPA)** - Separate entry points for different sections

### Development Tools
- **Poetry** - Package management and building
- **Pre-commit** - Code quality hooks
- **Pytest** - Testing framework with coverage
- **Ruff** - Python linting and formatting
- **MyPy** - Static type checking
- **Bandit** - Security analysis

## Project Structure

```
django-email-learning/
├── django_email_learning/          # Main Django app
│   ├── api/                        # REST API endpoints
│   ├── platform/                   # Web platform views
│   ├── templates/platform/         # Django templates with Vite integration
│   ├── models.py                   # Core data models
│   ├── admin.py                    # Django admin customization
│   ├── signals.py                  # Django signals for setup
│   └── decorators.py               # Authentication/authorization decorators
├── django_service/                 # Django project settings
├── frontend/                       # React frontend
│   ├── src/components/             # Shared React components
│   ├── courses/                    # Course management interface
│   ├── organizations/              # Organization management
│   └── users/                      # User management
├── tests/                          # Comprehensive test suite
└── scripts                         # Build automation scripts
```

## Core Models & Business Logic

### Key Models
1. **Organization** - Multi-tenant organization management
2. **OrganizationUser** - Role-based user membership (admin/editor/viewer)
3. **Course** - Educational courses with slug-based routing
4. **ImapConnection** - Encrypted IMAP server configurations
5. **Lesson** & **Quiz** - Course content types
6. **CourseContent** - Ordered content within courses

### Authentication & Authorization
- Django's built-in User model
- Role-based permissions via `OrganizationUser`
- Decorators: `@accessible_for()`, `@is_platform_admin()`, `@is_an_organization_member()`
- Session-based organization switching

### IMAP Integration
- Encrypted password storage using Fernet encryption
- Domain/IP validation for IMAP servers
- Support for email-based course interactions

## API Structure

### REST Endpoints
- **Organizations**: `/api/organizations/` - CRUD operations
- **Courses**: `/api/organizations/{id}/courses/` - Course management
- **IMAP Connections**: `/api/organizations/{id}/imap-connections/` - Email server setup
- **Session Management**: `/api/session` - Organization context switching

### Request/Response Handling
- Pydantic serializers for validation
- JSON-based API communication
- CSRF protection with cookie-based authentication
- Comprehensive error handling

## Frontend Architecture

### Multi-Page Setup
- **Vite MPA configuration** with separate entry points
- **Base component** for shared layout and navigation
- **Organization switcher** with session persistence
- **Responsive design** with mobile-friendly components

### Key Components
- **MenuBar** - Navigation with organization switching
- **Base** - Layout wrapper with breadcrumbs
- **CourseForm** - Course creation/editing with IMAP integration
- **FilterForm** - Course filtering interface
- **BottomDrawer** - Mobile-responsive filter drawer

### State Management
- Local storage for organization context
- Session-based backend synchronization
- Real-time organization switching

## Development Workflow

### Code Quality
- **Pre-commit hooks**: Ruff formatting, MyPy type checking, Bandit security
- **Test coverage**: 80% minimum with pytest-cov
- **Type safety**: Full MyPy compliance with Django stubs

### Build System
- **Poetry-based packaging** with custom build scripts
- **Pre/post-build hooks** for asset processing
- **Frontend asset integration** during packaging
- **Development vs. production** asset handling

### Testing Strategy
- **Unit tests** for models with fixtures
- **API integration tests** with role-based access testing
- **Comprehensive fixtures** for organizations, users, courses
- **Coverage reporting** with HTML and XML output

## Development Commands

```bash
# Setup
make dev-install              # Install development dependencies
poetry run pre-commit install # Setup git hooks

# Development
make dev                      # Setup development environment
poetry run python manage.py runserver  # Start Django server
cd frontend && npm run dev    # Start Vite dev server

# Testing & Quality
make test                     # Run test suite
poetry run pre-commit run --all-files  # Run all checks
make clean                    # Clean temporary files

# Building
make build                    # Build with pre/post hooks
make full-build               # Build including frontend assets
```

## Key Patterns & Conventions

### Django Patterns
- **Class-based views** with method decorators for permissions
- **Model validation** with custom `full_clean()` methods
- **Signal handlers** for automatic setup (groups, default organization)
- **Custom admin forms** with encrypted field handling

### Frontend Patterns
- **Functional components** with hooks
- **Prop drilling** for organization context
- **Material-UI theming** with custom color palette
- **Mobile-first responsive design**

### Security Patterns
- **Role-based access control** at view and API level
- **CSRF protection** with proper token handling
- **Password encryption** for IMAP credentials
- **Input validation** with Pydantic schemas

## Integration Points

### Django-Vite Integration
- **Template tags** for asset loading in development
- **Build-time asset processing** for production
- **Hot module replacement** during development
- **Static file management** for deployed assets

### CORS & Sessions
- **Cross-origin configuration** for development
- **Session-based authentication** with organization context
- **Cookie-based CSRF protection**
- **Trusted origins** configuration

## Common Development Tasks

### Adding New Models
1. Define model in `models.py` with proper validation
2. Create migration: `python manage.py makemigrations`
3. Add admin interface in `admin.py`
4. Create API serializers in `api/serializers.py`
5. Add API views with proper decorators
6. Write comprehensive tests

### Adding Frontend Components
1. Create component in appropriate directory
2. Add to existing page or create new entry point
3. Update Vite configuration if needed
4. Style with Material-UI theme
5. Handle responsive design

### Permission Management
- Use `@accessible_for({'admin', 'editor'})` for API endpoints
- Implement organization membership validation
- Handle superuser access patterns
- Test with different user roles

## Troubleshooting Common Issues

### CORS Errors
- Check `CSRF_TRUSTED_ORIGINS` in settings
- Verify cookie configuration for cross-origin requests
- Ensure proper headers in frontend API calls

### Build Issues
- Run `make clean` to clear caches
- Check Poetry lock file consistency
- Verify Node.js dependencies in frontend

### Test Failures
- Check database migrations are up to date
- Verify fixture dependencies
- Review test isolation issues

## Future Development Areas

### Planned Features
- **Email template system** for course delivery
- **Advanced quiz types** with multiple choice support
- **Course progress tracking** via email interactions
- **Bulk user management** interfaces

### Technical Improvements
- **Advanced caching** strategies
-
