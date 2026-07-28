# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Django Email Learning"
copyright = "2026, Payam Najafizadeh"
author = "Payam Najafizadeh"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib.googleanalytics",
]

googleanalytics_id = "G-67JHEC135G"
googleanalytics_enabled = True

templates_path = ["_templates"]
html_static_path = ["_static"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_logo = "_static/logo.png"

html_theme_options = {
    "light_css_variables": {
        "font-stack": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        "font-stack--headings": '"Bricolage Grotesque", Inter, -apple-system, BlinkMacSystemFont, sans-serif',
        "font-stack--monospace": "JetBrains Mono, Fira Code, monospace",
        "font-size--normal": "17px",
        "content-padding": "3em",
        "content-padding--small": "1.5em",
        # ink / paper / teal / violet — AvaCode design system tokens
        "color-background-primary": "#f8f8fb",
        "color-background-secondary": "#e8ecf1",
        "color-background-hover": "rgba(35, 41, 54, 0.05)",
        "color-background-border": "rgba(35, 41, 54, 0.1)",
        "color-foreground-primary": "#232936",
        "color-foreground-secondary": "#495062",
        "color-foreground-muted": "#646C80",
        "color-foreground-border": "rgba(35, 41, 54, 0.2)",
        "color-brand-primary": "#0E947E",
        "color-brand-content": "#0D7767",
        "color-link": "#0D7767",
        "color-link--hover": "#0E947E",
        "color-link-underline": "rgba(13, 119, 103, 0.3)",
        "color-link-underline--hover": "#0E947E",
        "color-sidebar-background": "#f8f8fb",
        "color-sidebar-caption-text": "#5947D3",
        "color-sidebar-link-text--top-level": "#232936",
        "color-highlight-on-target": "#D4F5EA",
        "color-admonition-title--note": "#0D7767",
        "color-admonition-title-background--note": "#EDFAF6",
        "color-admonition-title--tip": "#0D7767",
        "color-admonition-title-background--tip": "#EDFAF6",
        "color-admonition-title--hint": "#0D7767",
        "color-admonition-title-background--hint": "#EDFAF6",
        "color-admonition-title--seealso": "#0D7767",
        "color-admonition-title-background--seealso": "#EDFAF6",
        "color-admonition-title--important": "#4A3AB3",
        "color-admonition-title-background--important": "#F4F2FE",
    },
    "dark_css_variables": {
        "font-stack": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        "font-stack--headings": '"Bricolage Grotesque", Inter, -apple-system, BlinkMacSystemFont, sans-serif',
        "font-stack--monospace": "JetBrains Mono, Fira Code, monospace",
        # Furo's own light/dark split only overrides variables actually present
        # in this dict, but its light block applies unconditionally first — so
        # every neutral overridden above has to be re-pinned here to Furo's
        # real dark defaults, or it would leak the light-mode value into dark
        # mode. Only brand/link/accent colors below are deliberately changed.
        "color-background-primary": "#131416",
        "color-background-secondary": "#1a1c1e",
        "color-background-hover": "#1e2124",
        "color-background-border": "#303335",
        "color-foreground-primary": "#cfd0d0",
        "color-foreground-secondary": "#9ca0a5",
        "color-foreground-muted": "#81868d",
        "color-foreground-border": "#666",
        "color-sidebar-background": "#131416",
        "color-sidebar-link-text--top-level": "#cfd0d0",
        "color-brand-primary": "#38CBA6",
        "color-brand-content": "#6BDFBE",
        "color-link": "#6BDFBE",
        "color-link--hover": "#38CBA6",
        "color-link-underline": "rgba(107, 223, 190, 0.3)",
        "color-link-underline--hover": "#38CBA6",
        "color-sidebar-caption-text": "#8F7DEB",
        "color-highlight-on-target": "#0A4B43",
        "color-admonition-title--note": "#38CBA6",
        "color-admonition-title-background--note": "rgba(14, 148, 126, 0.15)",
        "color-admonition-title--tip": "#38CBA6",
        "color-admonition-title-background--tip": "rgba(14, 148, 126, 0.15)",
        "color-admonition-title--hint": "#38CBA6",
        "color-admonition-title-background--hint": "rgba(14, 148, 126, 0.15)",
        "color-admonition-title--seealso": "#38CBA6",
        "color-admonition-title-background--seealso": "rgba(14, 148, 126, 0.15)",
        "color-admonition-title--important": "#8F7DEB",
        "color-admonition-title-background--important": "rgba(89, 71, 211, 0.15)",
    },
    "source_repository": "https://github.com/AvaCodeSolutions/django-email-learning",
    "source_branch": "master",
    "source_directory": "docs/source/",
}

html_css_files = ["css/custom.css"]
