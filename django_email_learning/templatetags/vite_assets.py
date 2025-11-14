"""Template tags for loading Vite built assets."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()
logger = logging.getLogger(__name__)

# Cache for manifest file
_manifest_cache: Dict[str, Any] | None = None


def _load_manifest() -> Dict[str, Any]:
    """Load and cache the Vite manifest file."""
    global _manifest_cache
    
    if _manifest_cache is not None:
        return _manifest_cache
    
    # Look for manifest in static directory
    manifest_path = Path(settings.BASE_DIR) / "django_email_learning" / "static" / "manifest.json"
    
    if not manifest_path.exists():
        logger.warning(f"Vite manifest not found at {manifest_path}")
        return {}
    
    try:
        with open(manifest_path, "r") as f:
            _manifest_cache = json.load(f)
            return _manifest_cache
    except Exception as e:
        logger.error(f"Error loading Vite manifest: {e}")
        return {}


def _get_asset_urls(entry_key: str, manifest: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """
    Get script and CSS URLs for a given entry point.
    
    Returns:
        Tuple of (script_urls, css_urls)
    """
    if entry_key not in manifest:
        logger.warning(f"Entry key '{entry_key}' not found in manifest")
        return ([], [])
    
    entry = manifest[entry_key]
    script_urls = []
    css_urls = []
    
    # Add the main entry script
    script_urls.append(entry["file"])
    
    # Add CSS from the entry
    if "css" in entry:
        css_urls.extend(entry["css"])
    
    # Process imports (modulepreload)
    if "imports" in entry:
        for import_key in entry["imports"]:
            if import_key in manifest:
                import_entry = manifest[import_key]
                # Import scripts are added as modulepreload, not as script tags
                # CSS from imports should be included
                if "css" in import_entry:
                    css_urls.extend(import_entry["css"])
    
    return (script_urls, css_urls)


@register.simple_tag
def vite_asset_tags(entry: str) -> str:
    """
    Generate script and link tags for a Vite entry point.
    
    Usage:
        {% vite_asset_tags 'courses/index.html' %}
    """
    manifest = _load_manifest()
    if not manifest:
        return "<!-- Vite manifest not loaded -->"
    
    script_urls, css_urls = _get_asset_urls(entry, manifest)
    
    tags = []
    
    # Add CSS links
    for css_url in css_urls:
        tags.append(f'<link rel="stylesheet" crossorigin href="{settings.STATIC_URL}{css_url}">')
    
    # Add script tag for main entry
    for script_url in script_urls:
        tags.append(f'<script type="module" crossorigin src="{settings.STATIC_URL}{script_url}"></script>')
    
    # Add modulepreload for imports
    if entry in manifest and "imports" in manifest[entry]:
        for import_key in manifest[entry]["imports"]:
            if import_key in manifest:
                import_file = manifest[import_key]["file"]
                tags.append(f'<link rel="modulepreload" crossorigin href="{settings.STATIC_URL}{import_file}">')
    
    return mark_safe("\n    ".join(tags))
