"""Tests for vite_assets template tag."""

from unittest.mock import patch

import pytest
from django.template import Context, Template

from django_email_learning.templatetags.vite_assets import (
    _get_asset_urls,
    _load_manifest,
    vite_asset_tags,
)


@pytest.fixture
def mock_manifest() -> dict:
    """Create a mock manifest for testing."""
    return {
        "courses/index.html": {
            "file": "assets/courses-ABC123.js",
            "name": "courses",
            "src": "courses/index.html",
            "isEntry": True,
            "imports": ["_Base-XYZ789.js"],
        },
        "_Base-XYZ789.js": {
            "file": "assets/Base-XYZ789.js",
            "name": "Base",
            "css": ["assets/Base-STYLE.css"],
        },
    }


def test_load_manifest_returns_empty_dict_when_file_not_found() -> None:
    """Test that _load_manifest returns empty dict when file doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        result = _load_manifest()
        assert result == {}


def test_get_asset_urls_returns_correct_urls(mock_manifest: dict) -> None:
    """Test that _get_asset_urls returns correct script and CSS URLs."""
    script_urls, css_urls = _get_asset_urls("courses/index.html", mock_manifest)
    
    assert script_urls == ["assets/courses-ABC123.js"]
    assert css_urls == ["assets/Base-STYLE.css"]


def test_get_asset_urls_handles_missing_entry(mock_manifest: dict) -> None:
    """Test that _get_asset_urls handles missing entry gracefully."""
    script_urls, css_urls = _get_asset_urls("nonexistent/index.html", mock_manifest)
    
    assert script_urls == []
    assert css_urls == []


def test_vite_asset_tags_generates_correct_html(mock_manifest: dict) -> None:
    """Test that vite_asset_tags generates correct HTML tags."""
    with patch(
        "django_email_learning.templatetags.vite_assets._load_manifest",
        return_value=mock_manifest,
    ):
        result = vite_asset_tags("courses/index.html")
        
        # Check for CSS link
        assert '<link rel="stylesheet" crossorigin href="/static/assets/Base-STYLE.css">' in result
        
        # Check for script tag
        assert '<script type="module" crossorigin src="/static/assets/courses-ABC123.js"></script>' in result
        
        # Check for modulepreload
        assert '<link rel="modulepreload" crossorigin href="/static/assets/Base-XYZ789.js">' in result


def test_vite_asset_tags_returns_comment_when_no_manifest() -> None:
    """Test that vite_asset_tags returns a comment when manifest is not loaded."""
    with patch(
        "django_email_learning.templatetags.vite_assets._load_manifest",
        return_value={},
    ):
        result = vite_asset_tags("courses/index.html")
        assert result == "<!-- Vite manifest not loaded -->"


def test_vite_asset_tags_in_template(mock_manifest: dict) -> None:
    """Test that vite_asset_tags works in a Django template."""
    with patch(
        "django_email_learning.templatetags.vite_assets._load_manifest",
        return_value=mock_manifest,
    ):
        template = Template("{% load vite_assets %}{% vite_asset_tags 'courses/index.html' %}")
        rendered = template.render(Context({}))
        
        assert "assets/courses-ABC123.js" in rendered
        assert "assets/Base-STYLE.css" in rendered


def test_url_escaping_in_vite_asset_tags(mock_manifest: dict) -> None:
    """Test that URLs are properly escaped in vite_asset_tags."""
    # Create a manifest with special characters
    manifest_with_special_chars = {
        "test/index.html": {
            "file": "assets/test-ABC123.js",
            "name": "test",
            "src": "test/index.html",
            "isEntry": True,
            "imports": [],
        },
    }
    
    with patch(
        "django_email_learning.templatetags.vite_assets._load_manifest",
        return_value=manifest_with_special_chars,
    ):
        result = vite_asset_tags("test/index.html")
        
        # URLs should contain the original path (allowed characters)
        assert "assets/test-ABC123.js" in result
        
        # Should not contain unescaped problematic characters
        assert "<script" in result
        assert "crossorigin" in result
