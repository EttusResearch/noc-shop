# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add the site_gen directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'site_gen'))

from gen_noc_shop_list import generate_shop_list

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'NoC Shop'
copyright = '2025, Ettus Research'
author = 'Ettus Research'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_parser',
]

myst_enable_extensions = [
]

# change root doc to index (without extension)
root_doc = 'index'

templates_path = ['_templates']
exclude_patterns = []


source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'restructuredtext',
    '.md': 'markdown',
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']


# -- Custom setup function --------------------------------------------------

def setup(app):
    """Setup function to run before Sphinx builds the documentation."""
    app.connect('builder-inited', generate_shop_list_handler)
    return {'version': '1.0', 'parallel_read_safe': True}


def generate_shop_list_handler(app):
    """Event handler to generate the shop list before building."""
    # Change to the source directory to ensure relative paths work correctly
    original_dir = os.getcwd()
    source_dir = os.path.dirname(__file__)
    os.chdir(source_dir)
    
    try:
        generate_shop_list()
    finally:
        os.chdir(original_dir)
