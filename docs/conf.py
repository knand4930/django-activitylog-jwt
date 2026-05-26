from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

project = "django-activitylog-jwt"
author = "Nand Kishore"
release = "2.0.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

myst_heading_anchors = 3
suppress_warnings = ["myst.header", "myst.xref_missing"]
