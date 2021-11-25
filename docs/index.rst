.. arxiv_vanity_on_deck documentation master file, created by
   sphinx-quickstart on Thu Nov 25 16:08:47 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to arxiv_vanity_on_deck's documentation!
================================================

.. image:: https://mybinder.org/badge.svg
   :target: https://mybinder.org/v2/gh/mfouesneau/arxiv_vanity_on_deck/master
   :alt: Binder

This package is the next version of `arxiv_on_deck <https://github.com/mfouesneau/arxiv_on_deck>`_,
a quick and dirty version of the Arxiver.

This evolution uses `arXiv Vanity <https://www.arxiv-vanity.com/>`_ that renders academic papers from arXiv as responsive web pages.

This package searches for new articles on `ArXiv <https://arxiv.org/>`_ and renders their summary as Markdown documents.

The main goal of this package is to find papers authored by a given list of authors (e.g., a list of institute members) and only for those compiles a 1 page summary with figures (and captions).

It is a sort of Arxiver for institutes or groups

Examples of results
-------------------

.. toctree::
   :maxdepth: 2
   :caption: papers:
   :glob:

   examples/*


Examples
--------

.. image:: https://img.shields.io/badge/render%20on-nbviewer-orange.svg
   :target: https://nbviewer.org/github/mfouesneau/arxiv_vanity_on_deck/blob/main/examples/notebook.ipynb
   :alt: nbviewer


Generating a paper Markdown summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from arxiv_vanity_on_deck import (collect_summary_information,
                                    generate_markdown_text,
                                    highlight_authors_in_list,
                                    make_short_author_list)
   from arxiv_vanity_on_deck import mpia
   from requests.exceptions import HTTPError
   from IPython.display import Markdown

   # Get the list of authors by parsing the institute staff page
   mpia_authors = mpia.get_mpia_mitarbeiter_list()
   hl_list = [k[0] for k in mpia_authors]   # get last name only

   paper_id = "2111.06672"
   # Get the paper summary if the verifications are correct (e.g. affiliation keywords)
   content = collect_summary_information(paper_id, mpia.affiliation_verifications)
   content['authors'] = highlight_authors_in_list(content['authors'], hl_list)
   content['authors'] = make_short_author_list(content['authors'])
   with open(f'{paper_id}.md', 'w') as f:
      f.write(generate_markdown_text(content))

Parsing all new papers on ArXiv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from arxiv_vanity_on_deck import (get_new_papers,
                                    filter_papers)
   from arxiv_vanity_on_deck import mpia

   # Get author list
   mpia_authors = mpia.get_mpia_mitarbeiter_list()
   hl_list = [k[0] for k in mpia_authors]   # get last name only

   new_papers = get_new_papers()
   print("""Arxiv has {0:,d} new papers today""".format(len(new_papers)))
   keep, matched_authors = filter_papers(new_papers, list(set(hl_list)))
   identifiers = set([k.identifier.replace('arXiv:', '') for k in keep])
   print("""          {0:,d} with possible author matches""".format(len(identifiers)))

   # run the papers through vanity
   data = []
   for paper_id in identifiers:
      try:
         content = collect_summary_information(paper_id,
                                                mpia.affiliation_verifications)
         # Mitarbeiter list
         hl_list = [k[0] for k in mpia_authors]
         content['authors'] = highlight_authors_in_list(content['authors'], hl_list)
         content['authors'] = make_short_author_list(content['authors'])
         data.append(generate_markdown_text(content))
      except HTTPError as httpe:
         print(f"Error with paper {paper_id}... ({httpe})")
      except RuntimeError as re:
         print(f"Not an MPIA paper {paper_id}... ({re})")

   print("""Arxiv has {0:,d} new papers today""".format(len(new_papers)))
   print("""          {0:,d} with possible author matches""".format(len(identifiers)))
   print("""          {0:,d} fully extracted""".format(len(data)))



Contents
---------
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   arxiv_vanity_on_deck


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
