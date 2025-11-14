# Vite Asset Loading

This document explains how static assets from the Vite-built React frontend are loaded in Django templates.

## Overview

The package includes pre-built React frontend assets that are served as static files. The `vite_assets` template tag reads from a manifest file to dynamically load the correct hashed assets.

## How It Works

### 1. Build Process

When you run `./build_frontend.sh`:
1. Frontend is built using Vite
2. Vite generates hashed filenames (e.g., `courses-BqEDbcgx.js`)
3. Vite creates a `manifest.json` mapping entry points to actual files
4. Assets are copied to `django_email_learning/static/`

### 2. Manifest Structure

The `manifest.json` contains entries like:

```json
{
  "courses/index.html": {
    "file": "assets/courses-BqEDbcgx.js",
    "name": "courses",
    "isEntry": true,
    "imports": ["_Base-DIAH_WbB.js"],
    "css": ["assets/Base-CKtHFYfG.css"]
  },
  "_Base-DIAH_WbB.js": {
    "file": "assets/Base-DIAH_WbB.js",
    "css": ["assets/Base-CKtHFYfG.css"]
  }
}
```

### 3. Template Tag Usage

In your Django templates:

```django
{% extends "platform/base.html" %}
{% load vite_assets %}
{% block extra_head %}
    {% vite_asset_tags 'courses/index.html' %}
{% endblock %}
```

The `vite_asset_tags` tag will generate:
- `<link>` tags for CSS files
- `<script type="module">` tags for JavaScript entry points
- `<link rel="modulepreload">` tags for JavaScript dependencies

### 4. Generated HTML

The template tag generates HTML like:

```html
<link rel="stylesheet" crossorigin href="/static/assets/Base-CKtHFYfG.css">
<script type="module" crossorigin src="/static/assets/courses-BqEDbcgx.js"></script>
<link rel="modulepreload" crossorigin href="/static/assets/Base-DIAH_WbB.js">
```

## Security

- URLs are escaped using `urllib.parse.quote()` before rendering
- The manifest file is loaded from a trusted location (package static files)
- `mark_safe()` is only used after URL sanitization

## Caching

The manifest file is loaded once and cached in memory for performance. To clear the cache during development:

```python
from django_email_learning.templatetags import vite_assets
vite_assets._manifest_cache = None
```

## Development vs Production

### Production (Default)
- Uses pre-built assets from `django_email_learning/static/`
- No Vite dev server required
- Assets are included in the package

### Development with HMR
To use Vite's hot module replacement during development:

1. Install django-vite: `pip install django-vite`
2. Update settings.py to add django-vite
3. Temporarily modify templates to use `{% vite_asset %}` tags
4. Start Vite dev server: `cd frontend && npm run dev`

Note: This is optional and only for frontend development with live reloading.

## Rebuilding Assets

When you modify the React frontend:

```bash
./build_frontend.sh
```

This will rebuild the frontend and copy the new assets to the static directory.

## Troubleshooting

### "Vite manifest not loaded" comment in HTML

The manifest.json file was not found. Ensure:
1. The file exists at `django_email_learning/static/manifest.json`
2. Static files are properly collected: `python manage.py collectstatic`

### Assets not loading

Check:
1. `STATIC_URL` is correctly configured in settings
2. Static files middleware is enabled
3. The manifest contains the entry you're trying to load

### Wrong asset versions after rebuild

Clear the manifest cache:
```python
from django_email_learning.templatetags import vite_assets
vite_assets._manifest_cache = None
```

Or restart your Django development server.
