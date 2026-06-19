"""
Bootstrap a fresh Django dev project with django-email-learning pre-installed.

Registered as the `django-email-learning-init` console script.
"""

from __future__ import annotations

import re
import secrets
import subprocess
import sys
import venv
from pathlib import Path


# ── colours ──────────────────────────────────────────────────────────────────

BOLD = "\033[1m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
YELLOW = "\033[0;33m"
RESET = "\033[0m"


def info(msg: str) -> None:
    print(f"{CYAN}▸ {msg}{RESET}")


def success(msg: str) -> None:
    print(f"{GREEN}✔ {msg}{RESET}")


def warn(msg: str) -> None:
    print(f"{YELLOW}! {msg}{RESET}")


def header(msg: str) -> None:
    print(f"\n{BOLD}{msg}{RESET}")


def ask(prompt: str) -> str:
    return input(f"{BOLD}{prompt}{RESET}").strip()


# ── helpers ───────────────────────────────────────────────────────────────────


def generate_secret() -> str:
    return secrets.token_urlsafe(64)


def append_env(env_path: Path, key: str, value: str) -> None:
    content = env_path.read_text() if env_path.exists() else ""
    if re.search(rf"^{re.escape(key)}=", content, re.MULTILINE):
        warn(f"{key} already set in .env — skipping")
        return
    with env_path.open("a") as f:
        f.write(f"{key}={value}\n")


def run(args: list[str], **kwargs) -> None:  # type: ignore[type-arg]
    subprocess.run(args, check=True, **kwargs)


# ── steps ─────────────────────────────────────────────────────────────────────


def step_virtualenv(cwd: Path) -> str:
    """Ensure a virtualenv exists and return the path to its Python binary."""
    header("1/6  Virtual environment")

    if sys.prefix != sys.base_prefix:
        success(f"Already inside a virtual environment: {sys.prefix}")
        return sys.executable

    venv_dir = cwd / ".venv"
    if not venv_dir.exists():
        info("Creating .venv …")
        venv.create(str(venv_dir), with_pip=True)

    info("Using .venv …")
    python = str(venv_dir / "bin" / "python")
    success("Virtual environment ready")
    return python


def step_choose_features() -> tuple[bool, bool]:
    header("2/6  Optional features")

    print(
        f"{YELLOW}"
        "  AI text-editing lets instructors improve lesson content with AI assistance.\n"
        "  Currently only OpenAI is supported — you will need an OpenAI account and\n"
        "  an API key (https://platform.openai.com/api-keys)."
        f"{RESET}"
    )
    enable_ai = ask("  Enable AI text-editing features? (y/N) ").lower() == "y"

    print()
    print(
        f"{YELLOW}"
        "  Google Workspace group enrollment lets you bulk-enrol learners from a\n"
        "  Google Workspace directory. You will need a GCP project with an OAuth 2.0\n"
        "  Web Application credential. Set the authorised redirect URI to:\n"
        "    http://localhost:8000/oauth/google/callback/\n"
        "  Copy the Client ID and Client Secret from the GCP console\n"
        "  (https://console.cloud.google.com/apis/credentials)."
        f"{RESET}"
    )
    enable_google = (
        ask("  Enable Google Workspace group enrollment? (y/N) ").lower() == "y"
    )
    return enable_ai, enable_google


def step_install(python: str, enable_ai: bool, enable_google: bool) -> None:
    header("3/6  Installing packages")

    pip = [python, "-m", "pip", "install", "--quiet", "--upgrade"]

    info("Installing Django …")
    run(pip + ["django"])

    extras = ",".join(
        filter(None, ["ai" if enable_ai else "", "google" if enable_google else ""])
    )
    package = f"django-email-learning[{extras}]" if extras else "django-email-learning"
    info(f"Installing {package} …")
    run(pip + [package])

    info("Installing python-dotenv …")
    run(pip + ["python-dotenv"])

    success("Packages installed")


def step_secrets(cwd: Path) -> None:
    header("4/6  Dev secrets")

    env_path = cwd / ".env"
    env_path.touch()

    append_env(env_path, "SECRET_KEY", generate_secret())
    append_env(env_path, "JWT_SECRET_KEY", generate_secret())
    append_env(env_path, "ENCRYPTION_SECRET_KEY", generate_secret())

    success(".env written with SECRET_KEY, JWT_SECRET_KEY and ENCRYPTION_SECRET_KEY")


def step_optional_credentials(cwd: Path, enable_ai: bool, enable_google: bool) -> None:
    env_path = cwd / ".env"

    if enable_ai:
        print()
        openai_key = ask("  Enter your OPENAI_API_KEY: ")
        append_env(env_path, "OPENAI_API_KEY", openai_key)

        print()
        print("  Supported models:")
        print("    1) gpt-4o-mini  — balanced quality and speed")
        print("    2) gpt-5-nano   — smallest and fastest GPT-5 variant")
        print("    3) gpt-5-mini   — higher quality than nano, still efficient")
        choice = ask("  Select a model [1-3] (default 1): ")
        model = {"2": "gpt-5-nano", "3": "gpt-5-mini"}.get(choice, "gpt-4o-mini")
        append_env(env_path, "AI_TEXT_EDITING_MODEL", model)
        success(f"AI enabled with model: {model}")

    if enable_google:
        print()
        client_id = ask("  Enter GOOGLE_OAUTH_CLIENT_ID: ")
        append_env(env_path, "GOOGLE_OAUTH_CLIENT_ID", client_id)
        client_secret = ask("  Enter GOOGLE_OAUTH_CLIENT_SECRET: ")
        append_env(env_path, "GOOGLE_OAUTH_CLIENT_SECRET", client_secret)
        success("Google Workspace enrollment configured")


def step_scaffold(cwd: Path, python: str, enable_ai: bool, enable_google: bool) -> None:
    header("5/6  Django project")

    project_name = "myproject"
    manage_py = cwd / "manage.py"

    if manage_py.exists():
        warn("manage.py already exists — skipping project scaffold")
        return

    info(f"Scaffolding Django project '{project_name}' …")
    run([python, "-m", "django", "startproject", project_name, str(cwd)])

    settings_path = cwd / project_name / "settings.py"
    _patch_settings(settings_path, enable_ai, enable_google)
    success("settings.py patched")


def _patch_settings(settings_path: Path, enable_ai: bool, enable_google: bool) -> None:
    content = settings_path.read_text()

    env_loader = (
        "import os\n"
        "from pathlib import Path\n"
        "from dotenv import load_dotenv\n\n"
        "load_dotenv(BASE_DIR / '.env')\n\n"
    )
    content = content.replace("from pathlib import Path\n", env_loader, 1)

    # Wire SECRET_KEY to env
    content = content.replace(
        "SECRET_KEY = 'django-insecure",
        "SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure",
    )
    content = re.sub(
        r"(SECRET_KEY = os\.environ\.get\('SECRET_KEY', 'django-insecure[^']*')",
        r"\1)",
        content,
    )

    # Add django_email_learning to INSTALLED_APPS
    content = content.replace(
        "    'django.contrib.staticfiles',\n]",
        "    'django.contrib.staticfiles',\n    'django_email_learning',\n]",
    )

    # Build DJANGO_EMAIL_LEARNING config block as a single dict
    ai_block = (
        """
    "AI": {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "TEXT_EDITING_MODEL": os.environ.get("AI_TEXT_EDITING_MODEL", "gpt-4o-mini"),
    },"""
        if enable_ai
        else ""
    )
    google_block = (
        """
    "GOOGLE_OAUTH_CLIENT_ID": os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
    "GOOGLE_OAUTH_CLIENT_SECRET": os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),"""
        if enable_google
        else ""
    )

    del_config = f"""
# django-email-learning configuration
# See https://django-email-learning.readthedocs.io/en/latest/installation.html
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DJANGO_EMAIL_LEARNING = {{
    "BASE_DIR": BASE_DIR,
    "SITE_BASE_URL": os.environ.get("SITE_BASE_URL", "http://localhost:8000"),
    "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY"),
    "ENCRYPTION_SECRET_KEY": os.environ.get("ENCRYPTION_SECRET_KEY"),
    "FROM_EMAIL": os.environ.get("FROM_EMAIL", "webmaster@localhost"),{ai_block}{google_block}
}}
"""

    settings_path.write_text(content + del_config)


def step_migrate(python: str) -> None:
    header("6/6  Database")

    info("Running migrations …")
    run([python, "manage.py", "migrate"])


def print_done() -> None:
    print()
    print(
        f"{GREEN}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}"
    )
    print(
        f"{GREEN}{BOLD}║        django-email-learning is ready!                      ║{RESET}"
    )
    print(
        f"{GREEN}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}"
    )
    print()
    print("  Your dev environment has been configured with these defaults:")
    print("    • Database:      SQLite (db.sqlite3)")
    print("    • Email backend: Console (emails printed to terminal)")
    print("    • Logos:         Built-in defaults")
    print("    • Quiz settings: Default pass mark and attempt limits")
    print()
    print("  These are development defaults only. Before going to production,")
    print("  review the full installation guide for configuration options:")
    print()
    print(
        f"  {CYAN}📖 https://django-email-learning.readthedocs.io/en/latest/installation.html{RESET}"
    )
    print()
    print("  To start the dev server:")
    print(f"  {BOLD}  source .venv/bin/activate{RESET}")
    print(f"  {BOLD}  python manage.py runserver{RESET}")
    print()


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    cwd = Path.cwd()

    python = step_virtualenv(cwd)
    enable_ai, enable_google = step_choose_features()
    step_install(python, enable_ai, enable_google)
    step_secrets(cwd)
    step_optional_credentials(cwd, enable_ai, enable_google)
    step_scaffold(cwd, python, enable_ai, enable_google)
    step_migrate(python)
    print_done()


if __name__ == "__main__":
    main()
