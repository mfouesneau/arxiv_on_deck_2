#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
# sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution("arxiv_on_deck_2").version
except DistributionNotFound:
    __version__ = "unknown version"


# -- Project information -----------------------------------------------------

project = 'ArXiV on Deck 2'
copyright = '2021, Morgan Fouesneau'
author = 'Morgan Fouesneau'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
        "sphinx.ext.napoleon",
        "sphinx.ext.autodoc",
        "sphinx.ext.coverage",
        "sphinx.ext.doctest",
        "sphinx.ext.githubpages",
        "sphinx.ext.mathjax",
        "sphinx.ext.todo",
        "sphinx.ext.viewcode",
        "sphinx_autodoc_annotation",
        "myst_parser",
]

myst_enable_extensions = ["dollarmath", "colon_fence"]


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
    # '.ipynb': 'myst',
}

# The master toctree document.
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

html_theme_options = {
        'github_button': True,
        'github_user': 'mfouesneau',
        'github_repo': 'arxiv_vanity_on_deck',
        'github_banner': True,
}

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'alabaster'
html_theme = "sphinx_book_theme"

html_copy_source = True

html_show_sourcelink = True

html_sourcelink_suffix = ""

html_title = project

jupyter_execute_notebooks = "off"

execution_timeout = -1

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}
html_theme_options = {
    "path_to_docs": "docs",
    "repository_url": "https://github.com/mfouesneau/arxiv_vanity_on_deck",
    "launch_buttons": {
        "binderhub_url": "https://mybinder.org",
        "notebook_interface": "classic",
    },
    "use_edit_page_button": True,
    "use_issues_button": True,
    "use_repository_button": True,
    "use_download_button": True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# -- Options for the documentation -------------------------------------------
# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = True