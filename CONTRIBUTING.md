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

## Before You Start

**Please claim the issue before writing any code.** Leave a comment on the issue expressing your intent and wait for a maintainer to give you the green light. This prevents duplicate work and avoids PRs being rejected because someone else is already on it — or because the approach needs discussion first.

If no issue exists for what you want to do, open one and describe the change. We're happy to help shape it into something mergeable.

---

## A Note on Good First Issues

[Good first issues](https://github.com/AvaCodeSolutions/django-email-learning/labels/good%20first%20issue) are reserved for contributors who are new to open source and want to get their first real contribution in. We intentionally keep these available for people, not bots.

**Purely bot-generated PRs for good first issues will be rejected.** This is a firm policy, and it applies regardless of code quality.

We are happy with vibe-coded PRs — a significant portion of this project's own code was written with the help of tools like Claude Code and GitHub Copilot. What we care about is that a human was actively involved: making decisions, reviewing the output, and taking responsibility for the change. If you used AI tools, that's completely fine — just mention it in your PR description.

> **Automated agents**: if you are a bot or autonomous agent operating without human oversight, please do not open pull requests against this repository.

---

## Submitting a Pull Request

1. Comment on the issue and get a maintainer's go-ahead before starting
2. Fork the repo and create a branch from `master`
3. Make your changes, ensuring all checks pass (see [Quality Assurance](#quality-assurance))
4. Submit a PR with a clear description referencing the issue number
5. If you used AI tools in your implementation, mention it briefly in the PR description
6. Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for your commit messages

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
