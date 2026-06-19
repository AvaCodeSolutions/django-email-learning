"""
Bootstrap a fresh Django dev project with django-email-learning pre-installed.

Registered as the `django-email-learning-init` console script.
"""

from __future__ import annotations

import argparse
import itertools
import random
import re
import secrets
import subprocess
import sys
import threading
import time
import venv
from pathlib import Path


# ── colours ──────────────────────────────────────────────────────────────────

BOLD = "\033[1m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
YELLOW = "\033[0;33m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K\r"

QUIET = False


def info(msg: str) -> None:
    if not QUIET:
        print(f"{CYAN}▸ {msg}{RESET}")


def success(msg: str) -> None:
    if not QUIET:
        print(f"{GREEN}✔ {msg}{RESET}")


def warn(msg: str) -> None:
    print(f"{YELLOW}! {msg}{RESET}")


def header(msg: str) -> None:
    if not QUIET:
        print(f"\n{CYAN}{BOLD}{msg}{RESET}")


def ask(prompt: str) -> str:
    return input(f"{BOLD}{prompt}{RESET}").strip()


# ── spinner ───────────────────────────────────────────────────────────────────

INSTALL_QUIPS = [
    "Teaching emails new tricks…",
    "Brewing something great…",
    "Wiring up the curriculum…",
    "Summoning Django spirits…",
    "Packaging knowledge…",
    "Connecting the dots…",
    "Almost there, hang tight…",
]


class Spinner:
    def __init__(self, label: str) -> None:
        self._label = label
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self) -> None:
        frames = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
        quip = random.choice(INSTALL_QUIPS)
        while not self._stop_event.is_set():
            frame = next(frames)
            print(
                f"{CLEAR_LINE}{CYAN}{frame}{RESET} {self._label} {YELLOW}{quip}{RESET}",
                end="",
                flush=True,
            )
            time.sleep(0.08)

    def __enter__(self) -> Spinner:
        if not QUIET:
            self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop_event.set()
        if not QUIET:
            self._thread.join()
            print(CLEAR_LINE, end="", flush=True)


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
    header("1/7  Virtual environment")

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


def step_project_name() -> tuple[str, str]:
    header("2/7  Project name & URL prefix")

    name = ask("  Django project name (default: myproject): ") or "myproject"
    # sanitise: lowercase, replace spaces/hyphens with underscores
    name = re.sub(r"[-\s]+", "_", name.lower())
    name = re.sub(r"[^a-z0-9_]", "", name) or "myproject"
    success(f"Project name: {name}")

    prefix = (
        ask("  URL prefix for django-email-learning (default: email-learning): ")
        or "email-learning"
    )
    # strip leading/trailing slashes
    prefix = prefix.strip("/")
    success(f"URL prefix: /{prefix}/")
    return name, prefix


def step_choose_features() -> tuple[bool, bool]:
    header("3/7  Optional features")

    print(
        "  AI text-editing lets instructors improve lesson content with AI assistance."
    )
    print(f"  {CYAN}▸ Requires an OpenAI account and API key:{RESET}")
    print(f"  {CYAN}  https://platform.openai.com/api-keys{RESET}")
    enable_ai = ask("  Enable AI text-editing features? (y/N) ").lower() == "y"

    print()
    print(
        "  Google Workspace group enrollment lets you bulk-enrol learners from a\n"
        "  Google Workspace directory."
    )
    print(
        f"  {CYAN}▸ Requires a GCP project with an OAuth 2.0 Web Application credential.{RESET}"
    )
    print(f"  {CYAN}  Set the authorised redirect URI to:{RESET}")
    print(f"  {CYAN}    http://localhost:8000/oauth/google/callback/{RESET}")
    print(f"  {CYAN}  Then copy the Client ID and Secret from:{RESET}")
    print(f"  {CYAN}  https://console.cloud.google.com/apis/credentials{RESET}")
    enable_google = (
        ask("  Enable Google Workspace group enrollment? (y/N) ").lower() == "y"
    )
    return enable_ai, enable_google


def step_install(python: str, enable_ai: bool, enable_google: bool) -> None:
    header("4/7  Installing packages")

    pip = [python, "-m", "pip", "install", "--quiet", "--upgrade"]

    with Spinner("🦄 Installing Django …"):
        run(pip + ["django"])
    success("🦄 Django installed")

    extras = ",".join(
        filter(None, ["ai" if enable_ai else "", "google" if enable_google else ""])
    )
    package = f"django-email-learning[{extras}]" if extras else "django-email-learning"
    emoji = "🚀" if extras else "🦄"

    with Spinner(f"{emoji} Installing {package} …"):
        run(pip + [package])
    success(f"{emoji} {package} installed")

    with Spinner("Installing python-dotenv …"):
        run(pip + ["python-dotenv"])
    success("python-dotenv installed")


def step_secrets(cwd: Path) -> None:
    header("5/7  Dev secrets")

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


def step_scaffold(
    cwd: Path,
    python: str,
    project_name: str,
    url_prefix: str,
    enable_ai: bool,
    enable_google: bool,
) -> None:
    header("6/7  Django project")

    manage_py = cwd / "manage.py"

    if manage_py.exists():
        warn("manage.py already exists — skipping project scaffold")
    else:
        info(f"Scaffolding Django project '{project_name}' …")
        run([python, "-m", "django", "startproject", project_name, str(cwd)])

        settings_path = cwd / project_name / "settings.py"
        _patch_settings(settings_path, enable_ai, enable_google)
        success("settings.py patched")

        urls_path = cwd / project_name / "urls.py"
        _patch_urls(urls_path, url_prefix)
        success("urls.py configured")

        _create_login_template(cwd, project_name)

    _write_gitignore(cwd)

    info("Running migrations …")
    run([python, "manage.py", "migrate"])
    success("Database ready")


def step_superuser(python: str) -> None:
    header("7/7  Superuser")

    info("Creating a superuser account for the admin …")
    run([python, "manage.py", "createsuperuser"])


GITIGNORE_CONTENT = """
# Credentials — never commit these
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.egg
*.egg-info/
dist/
build/
.eggs/
wheels/

# Virtual environments
.venv/
venv/
env/
ENV/

# Django
*.log
db.sqlite3
db.sqlite3-journal
media/
staticfiles/
static/

# Coverage
.coverage
coverage.xml
htmlcov/

# Testing
.pytest_cache/
.tox/

# IDEs
.vscode/
.idea/
*.swp
*.swo
.DS_Store
""".lstrip()


def _write_gitignore(cwd: Path) -> None:
    gitignore = cwd / ".gitignore"
    if gitignore.exists():
        warn(".gitignore already exists — skipping")
        return
    gitignore.write_text(GITIGNORE_CONTENT)
    success(".gitignore created (includes .env)")


def _patch_urls(urls_path: Path, url_prefix: str) -> None:
    urls_path.write_text(
        f"""from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "{url_prefix}/",
        include("django_email_learning.urls", namespace="django_email_learning"),
    ),
    path(
        "",
        RedirectView.as_view(url="/{url_prefix}/platform/", permanent=False),
    ),
]
"""
    )


def _create_login_template(cwd: Path, project_name: str) -> None:
    """Create a minimal registration/login.html required by django.contrib.auth.urls."""
    templates_dir = cwd / project_name / "templates" / "registration"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "login.html").write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Log in</title>
  <style>
    body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }
    .card { background: #fff; padding: 2rem 2.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.1); width: 100%; max-width: 360px; }
    h1 { margin: 0 0 1.5rem; font-size: 1.4rem; }
    label { display: block; margin-bottom: .25rem; font-size: .9rem; font-weight: 600; }
    input[type=text], input[type=password] { width: 100%; padding: .5rem .75rem; margin-bottom: 1rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 1rem; }
    button { width: 100%; padding: .6rem; background: #0b74e5; color: #fff; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
    button:hover { background: #0960c4; }
    .errors { color: #c0392b; margin-bottom: 1rem; font-size: .9rem; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Log in</h1>
    {% if form.errors %}
      <p class="errors">Invalid username or password.</p>
    {% endif %}
    <form method="post">
      {% csrf_token %}
      <label for="id_username">Username</label>
      {{ form.username }}
      <label for="id_password">Password</label>
      {{ form.password }}
      <input type="hidden" name="next" value="{{ next }}">
      <button type="submit">Log in</button>
    </form>
  </div>
</body>
</html>
"""
    )

    # Register the templates directory in settings.py
    settings_path = cwd / project_name / "settings.py"
    content = settings_path.read_text()
    content = content.replace(
        '"DIRS": [],',
        f'"DIRS": [BASE_DIR / "{project_name}" / "templates"],',
        1,
    )
    settings_path.write_text(content)
    success("Login template created")


def _patch_settings(settings_path: Path, enable_ai: bool, enable_google: bool) -> None:
    content = settings_path.read_text()

    # Add dotenv import alongside the existing pathlib import
    content = content.replace(
        "from pathlib import Path\n",
        "from pathlib import Path\nfrom dotenv import load_dotenv\n",
        1,
    )

    # Add os import if not already present (Django's generated settings.py has none)
    if "import os\n" not in content:
        content = content.replace(
            "from pathlib import Path\n",
            "import os\nfrom pathlib import Path\n",
            1,
        )

    # Call load_dotenv after BASE_DIR is defined
    content = content.replace(
        "BASE_DIR = Path(__file__).resolve().parent.parent\n",
        "BASE_DIR = Path(__file__).resolve().parent.parent\n\nload_dotenv(BASE_DIR / '.env')\n",
        1,
    )

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


def print_done(project_name: str, url_prefix: str) -> None:
    print()
    print(
        f"{GREEN}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}"
    )
    print(
        f"{GREEN}{BOLD}║     🎉  django-email-learning is ready!                     ║{RESET}"
    )
    print(
        f"{GREEN}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}"
    )
    print()
    print(f"  Project: {BOLD}{project_name}{RESET}")
    print()
    print("  Your dev environment has been configured with these defaults:")
    print("    • Database:      SQLite (db.sqlite3)")
    print("    • Email backend: Console (emails printed to terminal)")
    print("    • Logos:         Built-in defaults")
    print("    • Quiz settings: Default pass mark and attempt limits")
    print()
    print("  URLs:")
    print(f"    • Platform:   http://localhost:8000/{url_prefix}/platform/")
    print("    • Admin:      http://localhost:8000/admin/")
    print("    • Login:      http://localhost:8000/accounts/login/")
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
    global QUIET  # noqa: PLW0603

    parser = argparse.ArgumentParser(
        description="Bootstrap a django-email-learning dev project"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress decorative output (for CI)"
    )
    args = parser.parse_args()
    QUIET = args.quiet

    cwd = Path.cwd()

    python = step_virtualenv(cwd)
    project_name, url_prefix = step_project_name()
    enable_ai, enable_google = step_choose_features()
    step_install(python, enable_ai, enable_google)
    step_secrets(cwd)
    step_optional_credentials(cwd, enable_ai, enable_google)
    step_scaffold(cwd, python, project_name, url_prefix, enable_ai, enable_google)
    step_superuser(python)
    print_done(project_name, url_prefix)


if __name__ == "__main__":
    main()
