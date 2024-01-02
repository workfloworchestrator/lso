# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
from importlib import import_module
from docutils.parsers.rst import Directive
from docutils import nodes
from sphinx import addnodes
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "lso")))


class RenderAsJSON(Directive):
    # cf. https://stackoverflow.com/a/59883833

    required_arguments = 1

    def run(self):
        module_path, member_name = self.arguments[0].rsplit(".", 1)

        member_data = getattr(import_module(module_path), member_name)
        code = json.dumps(member_data, indent=2)

        literal = nodes.literal_block(code, code)
        literal["language"] = "json"

        return [
            addnodes.desc_name(text=member_name),
            addnodes.desc_content("", literal)
        ]


def setup(app):
    app.add_directive("asjson", RenderAsJSON)


# -- Project information -----------------------------------------------------

project = "Lightweight Service Orchestrator"
copyright = "2023, GÉANT Vereniging"
author = "GÉANT Orchestration & Automation Team"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.todo"
]

templates_path = ["templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {"style_nav_header_background": "rgb(0 63 95)"}
html_css_files = ["custom.css"]
html_logo = "_static/geant_logo_white.svg"


# Both the class' and the ``__init__`` method's docstring are concatenated and inserted.
autoclass_content = "both"
autodoc_typehints = "none"

# Display todos by setting to True
todo_include_todos = True
