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

extensions = ["sphinxcontrib.googleanalytics"]

googleanalytics_id = "G-67JHEC135G"
googleanalytics_enabled = True

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"

html_theme_options = {
    "description": "A Django app for email-based learning management systems.",
    "logo": "logo.png",
    "github_user": "AvaCodeSolutions",
    "github_repo": "django-email-learning",
    "github_banner": True,
}
html_static_path = ["_static"]
