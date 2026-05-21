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
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_logo = "_static/logo.png"

html_theme_options = {
    "light_css_variables": {
        "font-stack": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        "font-stack--monospace": "JetBrains Mono, Fira Code, monospace",
        "font-size--normal": "17px",
        "content-padding": "3em",
        "content-padding--small": "1.5em",
    },
    "dark_css_variables": {
        "font-stack": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        "font-stack--monospace": "JetBrains Mono, Fira Code, monospace",
    },
    "source_repository": "https://github.com/AvaCodeSolutions/django-email-learning",
    "source_branch": "master",
    "source_directory": "docs/source/",
}

html_css_files = ["css/custom.css"]
