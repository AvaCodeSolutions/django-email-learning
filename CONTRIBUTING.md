# Contributing to django-email-learning

`django-email-learning` is a Django library for building email-based learning platforms — course delivery, IMAP-based response tracking, and React frontend components in one composable package. It powers [InboxAcademy](https://inboxacademy.io) in production.

Contributions of all kinds are welcome. Whether you're fixing a bug, improving docs, or proposing a new feature — we're glad you're here.

---

## Where to Start

- Browse [good first issues](https://github.com/AvaCodeSolutions/django-email-learning/labels/good%20first%20issue) if you're new to the project
- Check the [project roadmap](https://github.com/orgs/AvaCodeSolutions/projects/5/views/3) to see what's planned
- Join a [Discussion](https://github.com/AvaCodeSolutions/django-email-learning/discussions) to propose ideas or ask questions before opening a PR
- Comment on an existing [issue](https://github.com/AvaCodeSolutions/django-email-learning/issues) to share context or claim it

---

## Submitting a Pull Request

1. Open or find an issue for your change — if none exists, create one first
2. Fork the repo and create a branch from `master`
3. Make your changes, ensuring all checks pass (see [Quality Assurance](#quality-assurance))
4. Submit a PR with a clear description referencing the issue number
5. Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for your commit messages

   Examples:
   ```
   fix(imap): handle timeout on reconnect #42
   feat(courses): add support for multi-part email sequences #37
   docs: update setup instructions for Python 3.12
   ```

We aim to review pull requests within a few business days. You'll hear from a maintainer with feedback or approval.

---

## Setting Up Your Development Environment

### Backend

Requires Python ≥ 3.11. Dependencies are managed with [Poetry](https://python-poetry.org/).

```bash
# One-command setup: installs deps, pre-commit hooks, and runs migrations
make dev-init

# Start the backend server
make runserver
```

Or run steps individually:

```bash
make dev-install   # Install dependencies and set up pre-commit
make migrate       # Run migrations
make runserver     # Start the server
```

Run `make help` to see all available commands.

### Frontend

React + Vite, with source in `/frontend`. Both servers need to run during development.

```bash
# Recommended: start both concurrently
make -j start-dev
```

Or manually:

```bash
cd frontend
npm install
npm run dev
```

---

## Quality Assurance

Before submitting, make sure your code passes all checks:

```bash
make lint        # Run Ruff linting
make test        # Run tests with coverage (80% minimum)
make format      # Auto-format code
make pre-commit  # Run all pre-commit hooks
```

---

## Code Standards

| Area             | Tool / Rule                                                              |
|------------------|--------------------------------------------------------------------------|
| Type safety      | MyPy — all code must pass                                                |
| Linting & format | Ruff                                                                     |
| Test coverage    | ≥ 80%                                                                    |
| Security         | Bandit                                                                   |
| Commit style     | [Conventional Commits](https://www.conventionalcommits.org/) with issue number |

---

## License

By contributing, you agree that your work will be licensed under the project's [BSD 3-Clause License](./LICENSE). This allows broad reuse and redistribution, including commercial use.
