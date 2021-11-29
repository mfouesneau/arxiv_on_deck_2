# arxiv_on_deck_2

[![documentation](https://github.com/mfouesneau/arxiv_vanity_on_deck/actions/workflows/documentation.yml/badge.svg)](https://mfouesneau.github.io/arxiv_vanity_on_deck)

[![Binder](https://mybinder.org/badge.svg)](https://mybinder.org/v2/gh/mfouesneau/arxiv_vanity_on_deck/main)

This package is the next version of [arxiv_on_deck](https://github.com/mfouesneau/arxiv_on_deck),
a quick and dirty version of the Arxiver.

The main goal of this package is to find papers authored by a given list of authors (e.g., a list of institute members) and only for those compiles a 1 page summary with figures (and captions).

It is a sort of [Arxiver](https://arxiver.moonhats.com/) for institutes or groups

This evolution initially uses [arXiv Vanity](https://www.arxiv-vanity.com/) that renders academic papers from arXiv as responsive web pages.
This package cannot entirely rely on [arXiv Vanity](https://www.arxiv-vanity.com/) to render the documents correctly, and it is often having issues or incorrect rendering. Hence, it also implements latex parsing methods to extract information.

This package searches for new articles on [arXiv](https://arxiv.org/) and renders their summary as Markdown documents.
It does not compile the original LaTeX documents and only extracts the relevant information.



## Examples

[![nbviewer](https://img.shields.io/badge/render%20on-nbviewer-orange.svg)](https://nbviewer.org/github/mfouesneau/arxiv_vanity_on_deck/blob/main/examples/notebook.ipynb) view notebook
