# Contributing to Django Email Learning

Thank you for your interest in contributing!

This project is in an early development stage, and the core architecture is still evolving. For this reason, we currently accept a limited set of contribution types to keep the foundation stable and maintainable.

### At this stage, we only accept:

#### Discussions:
- Sharing ideas and feedback in [Github Discussions](https://github.com/AvaCodeSolutions/django-email-learning/discussions)
- Help in refining [the project](https://github.com/orgs/AvaCodeSolutions/projects/5/views/3) issues and roadmap
- Comments on existing [issues](https://github.com/AvaCodeSolutions/django-email-learning/issues)

#### Pull requests

- Small bug fixes
- Typo fixes
- Test improvement

When creating the PR, please follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) Specification for your commit message and make sure the commit message contains the issue number related to this change. If there is no issue for this change, please create an issue first.

> [!Important]
> By contributing your code, documentation, or other resources to this project, you agree that your contribution will be licensed under the project's BSD 3-Clause License. This license allows for broad reuse, modification, and distribution, including the ability for others to incorporate your work into their own products, both open source and commercial.

### Setup development environment
> [!Note]
> The project is in early development stage and the features are incomplete.

#### Backend:
For backend we are using Python>=3.11 and we use poetry for locking the dependencies.

1. Setup development environment (installs dependencies, pre-commit hooks, and runs migrations)
```shell
make dev-init
```

2. Start the backend server:
```shell
make runserver
```

Alternatively, you can run individual commands:
```shell
# Install dependencies and setup pre-commit
make dev-install

# Run migrations
make migrate

# Start server
make runserver
```

See all available commands with `make help`.

#### Frontend:
For frontend we are using React with Vite as the build tool and npm for managing dependencies. The frontend source code is in the `/frontend` directory. During development, you need both frontend and backend servers running.

**Option 1: Use Makefile (recommended)**
```shell
# Start both servers concurrently
make -j start-dev
```

**Option 2: Manual setup**

In a separate terminal, navigate to the frontend directory:
```shell
cd frontend

# Install node modules
npm install

# Run the development server
npm run dev
```

### Quality Assurance

Before submitting a pull request, ensure your code passes all checks:

```shell
# Run all linting checks
make lint

# Run tests with coverage
make test

# Format code
make format

# Run pre-commit hooks manually
make pre-commit
```

### Code Standards

- **Type Safety**: All Python code must pass MyPy type checking
- **Code Style**: Use Ruff for formatting and linting
- **Test Coverage**: Maintain minimum 75% test coverage
- **Security**: Code is scanned with Bandit for security issues
- **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/) specification
