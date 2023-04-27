.. arxiv_vanity_on_deck documentation master file, created by
   sphinx-quickstart on Thu Nov 25 16:08:47 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to ArXiV on Deck 2's documentation!
================================================

.. image:: https://mybinder.org/badge.svg
   :target: https://mybinder.org/v2/gh/mfouesneau/arxiv_on_deck_2/main
   :alt: Binder

This package is the next version of `arxiv_on_deck <https://github.com/mfouesneau/arxiv_on_deck>`_,
a quick and dirty version of the Arxiver.

The main goal of this package is to find papers authored by a given list of authors (e.g., a list of institute members) and only for those compiles a 1 page summary with figures (and captions).

It is a sort of `Arxiver <https://arxiver.moonhats.com/>`_ for institutes or groups

This evolution initially uses `arXiv Vanity <https://www.arxiv-vanity.com/>`_ that renders academic papers from arXiv as responsive web pages.
This package cannot entirely rely on `arXiv Vanity <https://www.arxiv-vanity.com/>`_ to render the documents correctly, and it is often having issues or incorrect rendering. Hence, it also implements latex parsing methods to extract information.

This package searches for new articles on `ArXiv <https://arxiv.org/>`_ and renders their summary as Markdown documents.
It does not compile the original LaTeX documents and only extracts the relevant information.

Rendering details
-----------------

.. toctree::
   :maxdepth: 2
   :glob:

   fromlatex

Examples of results
-------------------

.. toctree::
   :maxdepth: 2
   :caption: papers:
   :glob:

   examples/*


Contents
---------
.. toctree::
   :maxdepth: 2

   arxiv_on_deck_2


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
