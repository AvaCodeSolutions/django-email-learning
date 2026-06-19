#!/usr/bin/env bash
# Bootstrap a fresh Django dev project with django-email-learning pre-installed.
set -euo pipefail

# ── colours ──────────────────────────────────────────────────────────────────
BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[0;33m"
RESET="\033[0m"

info()    { echo -e "${CYAN}▸ $*${RESET}"; }
success() { echo -e "${GREEN}✔ $*${RESET}"; }
warn()    { echo -e "${YELLOW}! $*${RESET}"; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }
ask()     { echo -en "${BOLD}$*${RESET}"; }

# ── helpers ───────────────────────────────────────────────────────────────────
generate_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe(64))"
}

append_env() {
    # append KEY=VALUE only if KEY is not already in .env
    local key="$1" value="$2"
    if grep -q "^${key}=" .env 2>/dev/null; then
        warn "${key} already set in .env — skipping"
    else
        echo "${key}=${value}" >> .env
    fi
}

# ── 1. virtualenv ─────────────────────────────────────────────────────────────
header "1/6  Virtual environment"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ ! -d ".venv" ]]; then
        info "Creating .venv …"
        python3 -m venv .venv
    fi
    info "Activating .venv …"
    # shellcheck source=/dev/null
    source .venv/bin/activate
    success "Virtual environment active"
else
    success "Already inside a virtual environment: ${VIRTUAL_ENV}"
fi

# ── 2. install packages ───────────────────────────────────────────────────────
header "2/6  Installing packages"

info "Installing Django …"
pip install --quiet --upgrade django

info "Installing django-email-learning …"
pip install --quiet --upgrade django-email-learning

# ── 3. generate secrets ───────────────────────────────────────────────────────
header "3/6  Dev secrets"

touch .env

JWT_SECRET=$(generate_secret)
ENCRYPTION_SECRET=$(generate_secret)
DJANGO_SECRET=$(generate_secret)

append_env "SECRET_KEY"           "$DJANGO_SECRET"
append_env "JWT_SECRET_KEY"       "$JWT_SECRET"
append_env "ENCRYPTION_SECRET_KEY" "$ENCRYPTION_SECRET"

success ".env written with JWT_SECRET_KEY and ENCRYPTION_SECRET_KEY"

# ── 4. optional — AI features ─────────────────────────────────────────────────
header "4/6  AI features (optional)"

ask "Enable AI text-editing features? (y/N) "
read -r ai_choice

if [[ "${ai_choice,,}" == "y" ]]; then
    ask "  Enter your OPENAI_API_KEY: "
    read -r openai_key
    append_env "OPENAI_API_KEY" "$openai_key"

    echo ""
    echo "  Supported models:"
    echo "    1) gpt-4o-mini  — balanced quality and speed"
    echo "    2) gpt-5-nano   — smallest and fastest GPT-5 variant"
    echo "    3) gpt-5-mini   — higher quality than nano, still efficient"
    ask "  Select a model [1-3] (default 1): "
    read -r model_choice

    case "${model_choice}" in
        2) AI_MODEL="gpt-5-nano" ;;
        3) AI_MODEL="gpt-5-mini" ;;
        *) AI_MODEL="gpt-4o-mini" ;;
    esac

    append_env "AI_TEXT_EDITING_MODEL" "$AI_MODEL"
    success "AI enabled with model: ${AI_MODEL}"
else
    info "Skipping AI features"
fi

# ── 5. optional — Google Workspace group enrollment ───────────────────────────
header "5/6  Google Workspace group enrollment (optional)"

ask "Enable Google Workspace group enrollment? (y/N) "
read -r google_choice

if [[ "${google_choice,,}" == "y" ]]; then
    echo ""
    warn "You need a GCP project with an OAuth 2.0 Web Application credential."
    warn "Set the authorised redirect URI to:"
    warn "  http://localhost:8000/oauth/google/callback/"
    warn "Copy the Client ID and Client Secret from the GCP console."
    echo ""

    ask "  Enter GOOGLE_OAUTH_CLIENT_ID: "
    read -r google_client_id
    append_env "GOOGLE_OAUTH_CLIENT_ID" "$google_client_id"

    ask "  Enter GOOGLE_OAUTH_CLIENT_SECRET: "
    read -r google_client_secret
    append_env "GOOGLE_OAUTH_CLIENT_SECRET" "$google_client_secret"

    success "Google Workspace enrollment configured"
else
    info "Skipping Google Workspace enrollment"
fi

# ── 6. Django project scaffold ────────────────────────────────────────────────
header "6/6  Django project"

PROJECT_NAME="myproject"

if [[ ! -f "manage.py" ]]; then
    info "Scaffolding Django project '${PROJECT_NAME}' …"
    django-admin startproject "${PROJECT_NAME}" .

    # Patch settings.py to add django_email_learning and load .env secrets
    SETTINGS_FILE="${PROJECT_NAME}/settings.py"

    # Prepend env-loading imports at the top of settings.py
    python3 - <<PYEOF
import re

with open("${SETTINGS_FILE}", "r") as f:
    content = f.read()

env_loader = '''import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

'''

# Insert after the first 'from pathlib import Path' line
content = content.replace(
    "from pathlib import Path\n",
    env_loader,
    1,
)

# Wire SECRET_KEY to env
content = content.replace(
    "SECRET_KEY = 'django-insecure",
    "SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure",
)
# Close the os.environ.get call — find the closing quote of the insecure key
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

# Append DJANGO_EMAIL_LEARNING config block at the end
del_config = '''
# django-email-learning configuration
# See https://django-email-learning.readthedocs.io/en/latest/installation.html
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DJANGO_EMAIL_LEARNING = {
    "SITE_BASE_URL": os.environ.get("SITE_BASE_URL", "http://localhost:8000"),
    "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY"),
    "ENCRYPTION_SECRET_KEY": os.environ.get("ENCRYPTION_SECRET_KEY"),
    "FROM_EMAIL": os.environ.get("FROM_EMAIL", "webmaster@localhost"),
}
'''

ai_key = os.environ.get("AI_TEXT_EDITING_MODEL")
google_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")

if ai_key:
    del_config += '''
DJANGO_EMAIL_LEARNING["AI"] = {
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
    "TEXT_EDITING_MODEL": os.environ.get("AI_TEXT_EDITING_MODEL", "gpt-4o-mini"),
}
'''

if google_id:
    del_config += '''
DJANGO_EMAIL_LEARNING["GOOGLE_OAUTH_CLIENT_ID"] = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
DJANGO_EMAIL_LEARNING["GOOGLE_OAUTH_CLIENT_SECRET"] = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
'''

content += del_config

with open("${SETTINGS_FILE}", "w") as f:
    f.write(content)

print("settings.py patched")
PYEOF

    # Install python-dotenv so the settings file can load .env
    pip install --quiet python-dotenv

else
    warn "manage.py already exists — skipping project scaffold"
fi

# Run migrations
info "Running migrations …"
python3 manage.py migrate

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║        django-email-learning is ready!                      ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo "  Your dev environment has been configured with these defaults:"
echo "    • Database:      SQLite (db.sqlite3)"
echo "    • Email backend: Console (emails printed to terminal)"
echo "    • Logos:         Built-in defaults"
echo "    • Quiz settings: Default pass mark and attempt limits"
echo ""
echo "  These are development defaults only. Before going to production,"
echo "  review the full installation guide for configuration options:"
echo ""
echo -e "  ${CYAN}📖 https://django-email-learning.readthedocs.io/en/latest/installation.html${RESET}"
echo ""
echo "  To start the dev server:"
echo -e "  ${BOLD}  source .venv/bin/activate${RESET}"
echo -e "  ${BOLD}  python manage.py runserver${RESET}"
echo ""
