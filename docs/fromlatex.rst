Rendering from Latex source
===========================


The :mod:`arxiv_on_deck_2.latex` module provides all the functions and methods to extract and render Latex projects.

The main class :class:`arxiv_on_deck_2.latex.LatexDocument` handles the latex document interface. It parses the content of a give folder, and extract the title, authors, figures, and abstract of a documents.

There are multiple important steps in the processing of a Latex project folder.

1. :ref:`main_doc`
2. :ref:`inject_subdocs`
3. :ref:`validation`
4. :ref:`cleaning_source`
5. :ref:`parsing`: :ref:`parsing_title`, :ref:`parsing_authors`, :ref:`parsing_abstract`,  :ref:`parsing_figures`, and :ref:`parsing_bib``
6. :ref:`rendering`


.. _main_doc:

Finding the main document
-------------------------

It is very common to have multiple `.tex` files in a project. The main document is
the one that contains the `documentclass` command.

.. warning::

    It is important to note that the code cannot make a distinction between `.tex` files, hence if two of those have a `documentclass` command it is unclear which one is the main document.

.. seealso::

    :func:`arxiv_on_deck_2.latex.find_main_doc`.


.. _inject_subdocs:

Flattening document
-------------------

One common practice in writting documents is to have `include` or `input` commands in the main document. Having multiple files allows to have clean main tex, and facilitate working with multiple contributors. For instance, tables are often from a different file.

For every `include` or `input` command in the main document, we replace the command by the content of the referenced file. This step is called _flattening_: it removes the nested structure of the document.

.. seealso::

    :func:`arxiv_on_deck_2.latex.inject_other_sources`.


.. _validation:

Validation step (optional)
--------------------------

In our application, we do not want to process documents that are not meeting some criteria (e.g., presence of affiliation keywords). It is at this stage that we check for affiliations, i.e., after flattening the document (sometimes a separate file provides the authors and affiliations.)

:class:`arxiv_on_deck_2.latex.LatexDocument` takes a `validation` optional keyword argument. It corresponds to a function applied to the document source. We use this function to raise an exception and stop the procedure.

.. code-block:: python
    :caption: Example of validation function

    def validation(source: str):
        """Raises error paper during parsing of source file"""
        check = mpia.affiliation_verifications(source, verbose=True)
        if check is not True:
            raise ValueError("mpia.affiliation_verifications: " + check)


.. seealso::

    :func:`arxiv_on_deck_2.mpia.affiliation_verifications`.


.. _cleaning_source:

Source code preprocessing (cleaning)
------------------------------------

Latex is a power and flexible language. However, the drawback is that there is not a universal manner to setup a document and to write the content of it.

We first remove any commented lines (or ends of lines) from the source (:func:`arxiv_on_deck_2.latex.clear_latex_comments`) as well as series of empty lines (multiple empty lines become a single empty line).

We also remove `$$` which has the issue of defining inline equation block but more often concatenate inline math blocks. It is very difficult to find when `$$` means something important in this context.

We parse the header of the main document for macros.

We clean the text for markdown special character:

* :kbd:`\`\`` and :kbd:`''` become :kbd:`"`
* Forced spaces in Latex are remove. Multiple spaces are reduced to single space characters. (e.g., :kbd:`~`  and :kbd:`\\,` )
* Accents are replaced by their corresponding unicode character. (e.g., :kbd:`\\~{n}`, :kbd:`ñ`)
* Finally, we replace common journal macros for figures to use ``\includegraphics`` instead.

.. warning::

    * prefer ``\begin{equation}...\end{equation}`` (and similar) to ``$$ ... $$``.
    * avoid mixing ``\def``, ``\gdef`` (see latex documentation).
    * Use proper declarations: ``\def\name{..}`` should read ``\def{\name}{}`` and ``\newcommand\name[n]{..}`` should read ``\newcommand{\name}[n]{}``.

.. _parsing:

Parsing the TeX source
----------------------

The heavy lifting is mostly done by `TeXSoup <https://texsoup.alvinwan.com/>`_. TexSoup is a Python3 library for extracting data from Latex files. It is very much inspired by `BeautifulSoup <https://www.crummy.com/software/BeautifulSoup/bs4/doc/>`_. It turns even invalid sources into a structure that you can navigate, search, and modify.

We do not aim to retrieve every bit of the document. We are not trying to reproduce `ArXiv Vanity <https://www.arxiv-vanity.com/>`_. We do not need the exact text throughout the paper, so we can try to isolate potential error parts and remove them.
(see :func:`arxiv_on_deck_2.latex.get_content`). However, it is not always clear where a document can be broken and removing random parts does not always lead to a struturally correct document (removing endings of environments, for instance). Automated cleaning is not always possible.

.. _parsing_debug:

Debugging document
~~~~~~~~~~~~~~~~~~

We recomment instead to identify where there could be an issue. We use the following example which attempts to parse the source per section.

.. code-block:: python
    :caption: Bracketting problematic tex source errors

    from TexSoup import TexSoup
    import re

    def bracket_error(source: str):
        """ Find problematic portions of the document """

        # Checking header
        begin_doc = next(re.finditer(r'\\begin\{document\}', doc.source)).span()[1]
        header = source[:begin_doc]
        text = header + r"\n\end{document}"

        try:
            print("Header check... ", end='')
            TexSoup(text)
            print("ok")
        except:
            print("error")
            raise RuntimeError("Error in the header")

        # Check the text per section until the end.
        # Do not stop and try them all.

        problematic_text = []

        sections = ([(0, begin_doc, 'until first section')] +
                    [(g.span()[0], g.span()[1], g.group()) for g in re.finditer(r'\\section\{.*\}', source)] +
                    [(g.span()[0], g.span()[1], g.group()) for g in re.finditer(r'\\begin\{appendix\}', source)]
                )

        sections = sorted(sections, key=lambda x: x[0])

        prev_pos, prev_name = (0, 'header')
        for span, span_end, name in sections:
            text = source[prev_pos:span]
            if prev_pos > begin_doc:
                text = r"\n\begin{document}" + text + r"\n\end{document}"
            else:
                text = text + r"\n\end{document}"
            try:
                print(f"{prev_pos}:{prev_name}-->{span}:{name} check... ", end='')
                TexSoup(text, tolerance=1)  # allow not ending env
                print("ok")
                prev_pos = span
                prev_name = name
            except:
                print(f"error between {prev_pos} and {span}")
                problematic_text.append((prev_pos, source[prev_pos:span]))
                prev_pos = span
                prev_name = name
                # raise
        return problematic_text

Once we identify the section, we can try to further isolate the problematic Tex environement with the following.

.. code-block:: python
    :caption: Example of problematic environement

    def check_environment(text, offset=0):
    """ Check environment """
    env = re.compile(r"\\begin\{(?P<env>.*)\}(.*)\\end\{(?P=env)\}", re.DOTALL)

    for match in env.finditer(text):
        beg, end = match.span()
        beg += offset
        end += offset
        envname = match.groups()[0]
        try:
            latex.TexSoup(match.group())
        except:
            print(f"Error in {envname:s} between {beg} and {end}")
            return match.groups()[1], beg, end


.. seealso::

    `TeXSoup <https://texsoup.alvinwan.com/>`_


.. _parsing_macros:

Handling Macros
~~~~~~~~~~~~~~~

We detect macros defined in the header (see :func:`arxiv_on_deck_2.latex.LatexDocument.retrieve_latex_macros`).

A detected macro definition is one of the following tex command ``\providecommand``, ``\command``, ``\newcommand``, ``\renewcommand``, ``\def``, ``\gdef``). We need some precaution as these can only be MathJax text,  we need to enforce `math` mode: :kbd:`$` (with any spacing) are removed.

We also provide default macros, typical for academic publications:

* ``\newcommand{\ensuremath}{}``
* ``\newcommand{\xspace}{}``
* ``\newcommand{\object}[1]{\texttt{#1}}``
* ``\newcommand{\farcs}{{.}''}``
* ``\newcommand{\farcm}{{.}'}``
* ``\newcommand{\arcsec}{''}``
* ``\newcommand{\arcmin}{'}``
* ``\newcommand{\ion}[2]{#1#2}``

.. _parsing_title:

Title and subtitle
~~~~~~~~~~~~~~~~~~

The command ``\title`` is used to define the abstract of the document regardless of the journal class.
We parse both commands and if present, we concatenate the title and subtitle with a `:` (see :func:`arxiv_on_deck_2.latex.LatexDocument.get_title`).

.. _parsing_abstract:

Abstract
~~~~~~~~
The command ``\abstract`` or environement ``\begin{abstract}...\end{abstract}`` are used to define the abstract of the document regardless of the journal class. Sometimes it has one or multiple arguments. We extract all arguments and store the text as the abstract of the document (see :func:`arxiv_on_deck_2.latex.LatexDocument.get_abstract`).

.. _parsing_authors:

Authors
~~~~~~~

The definition of authors in the usual Journal Tex classes is very non-universal. Some of them allow `ORCID <orcid.org>`_, some do not, which often leads to ad-hoc additional macros. We parse the author list (indicated by ``\author``) store the text as the authors (see :func:`arxiv_on_deck_2.latex.LatexDocument.get_authors`).

.. warning::

    The parsing of the authors does not always return correct information. This function will be refined in further versions.


We also provide a short author list, which by default turns a five and more author list into first author, et al. (see :func:`arxiv_on_deck_2.latex.LatexDocument.short_authors`).

.. _parsing_figures:

Figures
~~~~~~~

Often authors like to use specifications for their ``\graphicspath``. We parse the header of the document for this specific macro and we propagate it to the extraction of the figures.

For each ``\figure`` and ``\\figure*`` environement, we extract the image file references (sometimes multiple files), the caption and label. (see :func:`arxiv_on_deck_2.latex.LatexDocument.get_all_figures`)

We assume images refered by ``\includegraphics`` (we cleaned the text from ``\plotone``, ``\plottwo`` in the preprocessing). We also verify that the file(s) exist (see :func:`arxiv_on_deck_2.latex.find_graphics`).

Finally we use the  :class:`arxiv_on_deck_2.latex.LatexFigure` class to store the extracted information. This class allows us to handle multiple figures and final rendering. In particular, we have a special handling for `pdf` and `eps` figures to convert them to `png` images (see :func:`arxiv_on_deck_2.latex.convert_pdf_to_image` and :func:`arxiv_on_deck_2.latex.convert_eps_to_image`).

.. _parsing_bib:

Bibliography
~~~~~~~~~~~~

The bibliographic references in articles are important and often used in figure captions. It is therefore important to parse them in a readable format. We handle all references assuming a base of `bibtex` information using [Pybtex](https://pybtex.org/).

We first look for a `.bbl` file in the document's directory. This file corresponds to a compiled bibliography and links from the main document (usually generated by `bibtex`). When present, this ensure that we have matching bibliographic references in the document. One major issue with `.bbl` files is that the compiled references match the journal style and thus authors may be given in different formats (e.g. with commas, with initial first etc.). We parse, clean and organize this content to recreate a structured `bibtex` content from the `.bbl` file (see :func:`arxiv_on_deck_2.latexbib.parse_bbl``)

If we cannot find or parse the `.bbl` file, we extract the `.bib` reference in the main document. However, sometimes, authors do not provide their bibliographic file with their document.

.. warning::

    We currently do not support manual definitions in the main document (e.g. ``\bibitem``).


.. _rendering:

Summary Rendering
-----------------

We designed this version of `ArXiV on Deck` to output Markdown text. John Gruber and Aaron Swartz created Markdown in 2004 as a lightweight markup language for creating formatted ascii text, i.e. readable by a human in its source form. It has the advantage to be completely independent from a TeX compiler and packages. One only needs MathJax (or similar) to render the mathematical bits of the document in a nicer way than TeX code (still readable).

Our summary contains the title, authors, comments, and three figures (with captions).

Highlighting authors
~~~~~~~~~~~~~~~~~~~~

The author list can also highlight some of the authors, for instance co-authors from an institute.

We highlight authors in a document through the :func:`arxiv_on_deck_2.latex.LatexFigure.highlight_authors_in_list` function.
Any author matching names in the provided list will be tagged with ``<mark>...</mark>``.

Selection of figures
~~~~~~~~~~~~~~~~~~~~

For the summary, we select three figures from the paper. The selection is currently based on the most refered figures based on their labels (see :func:`arxiv_on_deck_2.latex.select_most_cited_figures`).

.. warning::

    The figure selection remains simple in this version.
    Currently, the Arxiver tag is not used:  `%@arxiver{fig1.pdf,fig4.png,fig15.eps}`, but will be included in a future version.


Additional macros
~~~~~~~~~~~~~~~~~

As it is common for a paper to come with a suite of user defined macros, we need to include them in the output.
We include them in a HTML div: ``<div class="macros" style="visibility:hidden;">`` to help the rendering layout.
see :func:`arxiv_on_deck_2.latex.get_macros_markdown_text`.

We make sure that all calls to macros are in tex math mode to be handled by Mathjax or other processor (see: :func: `arxiv_on_deck_2.latex.force_mathmode`)

Replace citation macros
~~~~~~~~~~~~~~~~~~~~~~~

For any of ``\citet``, ``\citep``, ``\citealt``, ``\cite`` command calls (in the summary content only), we replace the macro with a markdown equivalent using the bibliographic data we extracted from the main document. (see: :func:`arxiv_on_deck_2.latexbib.replace_citations`) We render the citations with the astronomy standard of giving the first author et al. and year of the paper (see: :func:`arxiv_on_deck_2.latexbib.LatexBib.get_citation_md`). If we can find a URL (`url` or `adsurl``) or `doi`, we create an hyperlink with the citation text (see: :func:`arxiv_on_deck_2.latexbib.LatexBib.get_url`).

Layout
~~~~~~

The layout is basic from the Markdown source. To help potentially more complex presentation,
we add HTML div to the document. Below is what a document looks like:

.. code-block:: text

    <div class="macros" style="visibility:hidden;">
    $\newcommand{\ensuremath}{}$
    $\newcommand{\xspace}{}$
    $\newcommand{\object}[1]{\texttt{#1}}$
    </div>

    <div id="title">

    # Title

    </div>

    <div id="comments">

    [![arXiv](https://img.shields.io/badge/arXiv-<paper_id>-b31b1b.svg)](https://arxiv.org/abs/<paper_id>) _Some comments_

    </div>

    <div id="authors">

    first author, et al. -- incl., <mark>highlighted author</mark>

    </div>

    <div id="abstract">

    **Abstract:** The abstract of the text.

    </div>

    <div id="div_fig1">

    <img src="tmp_<paper_id>/figname9a.png" alt="Fig9.1" width="50%"/><img src="tmp_<paper_id>/figname9b.png" alt="Fig9.2" width="50%"/>

    **Figure 9. -** Caption of the two panel figure 9.

    </div>
    <div id="div_fig2">

    <img src="tmp_<paper_id>/fig3.png" alt="Fig3" width="100%"/>

    **Figure 3. -** Caption of Fig 3.

    </div>
    <div id="div_fig3">

    <img src="tmp_<paper_id>/fig10.png" alt="Fig10" width="100%"/>

    **Figure 10. -** Caption of Fig 10.

    </div>

Thanks to these divisions (`<div>`) one can change the CSS properties to render the summary as they prefer.