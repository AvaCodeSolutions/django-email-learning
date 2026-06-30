import argparse
import json
import re
from pathlib import Path

TEMPLATES = [
    ["platform", "courses"],
    ["platform", "course"],
    ["platform", "organizations"],
    ["platform", "organization"],
    ["platform", "learners"],
    ["platform", "settings_api_keys"],
    ["platform", "analytics"],
    ["platform", "newsletter"],
    ["platform", "newsletter_subscribers"],
    ["personalised", "quiz_public"],
    ["personalised", "assignment_public"],
    ["personalised", "command_result"],
    ["personalised", "certificate"],
    ["personalised", "certificate_form"],
    ["public", "organization"],
    ["public", "course"],
]


def rewrite_backend_file(backend_file: Path, manifest: dict, frontend_path: str) -> None:
    file_content = backend_file.read_text()
    file_content = file_content.replace("{% load django_vite %}", "")
    file_content = file_content.replace("{", "{{").replace("}", "}}")
    search_result = re.search("{{% vite_asset.*%}}", file_content)
    if not search_result:
        print(f"No vite asset tag found in {backend_file}")
        return
    vite_asset_tag = search_result.group(0)
    new_content = file_content.replace(vite_asset_tag, "{manifest_tags}")

    main_manifest = manifest.get(frontend_path, {})
    script_tags = [f'<script type="module" crossorigin src="/static/{main_manifest.get("file", "")}"></script>']
    css_tags = []
    for css_file in main_manifest.get("css", []):
        css_tags.append(f'<link rel="stylesheet" href="/static/{css_file}">')
    link_tags = []
    for item in main_manifest.get("imports", []):
        link_tags.append(f'<link rel="modulepreload" crossorigin href="/static/assets/{item.lstrip("_")}">')
        if item in manifest:
            for css_file in manifest[item].get("css", []):
                css_tags.append(f'<link rel="stylesheet" href="/static/{css_file}">')

    manifest_tags = "\n    ".join(link_tags + css_tags + script_tags)
    new_content = new_content.format(manifest_tags=manifest_tags)
    backend_file.write_text(new_content)


def run_prebuild() -> None:
    print("Running pre-build script...")
    # Add pre-build logic here

    root_path = Path(__file__).resolve().parent.parent
    manifest_path = root_path / "dist" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    for template_path in TEMPLATES:
        template_path.append("index.html")
        frontend_path = "/".join(template_path).lstrip("/")
        backend_file = root_path / "django_email_learning" / "templates" / template_path[0] / f"{template_path[1]}.html"
        rewrite_backend_file(backend_file, manifest, frontend_path)

    folders_with_base_html = {"platform", "personalised", "public"}

    for folder in folders_with_base_html:
        base_html_path = root_path / "django_email_learning" / "templates" / folder / "base.html"
        file_content = base_html_path.read_text()
        file_content = file_content.replace("{% load django_vite %}", "")
        file_content = file_content.replace("{% vite_react_refresh %}", "")
        file_content = file_content.replace("{% vite_hmr_client %}", "")
        base_html_path.write_text(file_content)


if __name__ == "__main__":
    args = argparse.ArgumentParser(description="Build script for the project.")
    args.add_argument(
        "--prebuild",
        help="Modifies django template files and replaces vite tags with tags to load built assets.",
        action="store_true",
    )
    parsed_args = args.parse_args()

    if parsed_args.prebuild:
        run_prebuild()
