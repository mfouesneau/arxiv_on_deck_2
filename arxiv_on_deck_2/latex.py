from glob import glob
import warnings
import pathlib
from typing import Union, Sequence
import re
from TexSoup import TexSoup
try:
    from IPython.display import Markdown
except ImportError:
    Markdown = None
from pdf2image import convert_from_path
# Requires poppler system library
# !pip3 install pdf2image


def _warning_on_one_line(message, category, filename, lineno, file=None, line=None) -> str:
    """ Prints a complete warning that includes exactly the code line triggering it from the stack trace. """
    return " {0:s}:{1:d} {2:s}:{3:s}".format(filename, lineno,
                                             category.__name__, str(message))

class LatexWarning(UserWarning):
    pass


# set default
warnings.simplefilter('always', LatexWarning)


def drop_none_from_list(list_: Sequence) -> Sequence:
    """ Remove None from a list """
    return [k for k in list_ if k is not None]


def find_main_doc(folder: str) -> Union[str, Sequence[str]]:
    """ Attempt to find which TeX file is the main document.

    :param folder: folder containing the document
    :return: filename of the main document
    """

    texfiles = list(pathlib.Path(f"{folder}").glob("**/*.tex"))

    if (len(texfiles) == 1):
        return str(texfiles[0])

    warnings.warn(LatexWarning('Multiple tex files.\n'), stacklevel=4)
    selected = None
    for e, fname in enumerate(texfiles):
        with open(fname, 'r', errors="surrogateescape") as finput:
            if 'documentclass' in finput.read():
                selected = e, fname
                break
    if selected is not None:
        warnings.warn(LatexWarning(
            "Found documentclass in {0:s}\n".format(str(selected[1]))), stacklevel=4)
    else:
        raise RuntimeError('Could not locate the main document automatically.'
                           'Little help please!')
    return str(selected[1])


def convert_pdf_to_image(fname: str) -> str:
    """ Convert image from PDF to png.

    The new image is stored with the original one

    :param fname: file to potentially convert
    """
    from pdf2image import convert_from_path
    pages = convert_from_path(fname, dpi=500, use_cropbox=True)
    rootname = fname.replace('.pdf', '')
    if len(pages) > 1:
        for num, page in enumerate(pages, 1):
            page.save(f'{rootname}.{num:d}.png', 'PNG')
        return f'{rootname}.*.png'
    else:
        pages[0].save(f'{rootname}.png', 'PNG')
        return f'{rootname}.png'


class LatexFigure(dict):
    """ Representation of a figure from a LatexDocument

    A dictionary-like structure that contains:
    - num: figure number
    - caption: figure caption
    - label: figure label
    - images: list of images

    """
    def __init__(self, **data):
        super().__init__(data)
        self._check_pdf_figure()

    def _check_pdf_figure(self):
        """ Check if PDF images and convert to PNG if needed """
        images = self['images']
        new_images = []
        for image in images:
            if image[-4:] == '.pdf':
                new_images.append(convert_pdf_to_image(image))
            else:
                new_images.append(image)
        self['images'] = new_images

    def generate_markdown_text(self):
        """  Generate the markdown summary

        :return: markdown text
        """
        if (len(self['images']) > 1):
            width = 100 // len(self['images'])
            num = self['num']
            current = ''.join(
                [f'<img src="{figsub}" alt="Fig{num:d}.{sub:d}" width="{width}%"/>'
                 for sub, figsub in enumerate(self['images'], 1)]
            )
        else:
            # current = "![Fig{num:d}]({image})".format(num=self['num'], image=self['images'][0])
            current = '<img src="{image}" alt="Fig{num:d}" width="100%"/>'.format(num=self['num'], image=self['images'][0])

        return """{current}\n\n**Figure {num}. -** {caption} (*{label}*)""".format(current=current, **self)

    def _repr_markdown_(self):
        if Markdown is None:
            raise ImportError('could not import `IPython.display.Markdown`')
        return Markdown(self.generate_markdown_text())._repr_markdown_()


def select_most_cited_figures(figures: Sequence[LatexFigure],
                              content: dict,
                              N: int = 3) -> Sequence[LatexFigure]:
    """ Finds the number of references to each figure and select the N most cited ones

    :param figures: list of all figures
    :param content: paper content from TexSoup
    :param N: number of figures to select
    :return: list of selected figures
    """
    # Find the number of references to each figure
    sorted_figures = sorted([(content.text.count(fig['label']), fig) for fig in figures],
                            key=lambda x: x[0], reverse=True)
    selected_figures = [k[1] for k in sorted_figures[:N]]
    return selected_figures


def clear_latex_comments(data: str) -> str:
    """ clean text from any comment

    :param data: text to clean
    :return: cleaned text
    """
    lines = []
    for line in data.splitlines():
        try:
            start = list(re.compile(r'(?<!\\)%').finditer(line))[0].span()[0]
            lines.append(line[:start])
        except IndexError:
            lines.append(line)
    return '\n'.join(lines)


def fix_def_command(text: str) -> str:
    ''' Fixing a small bug in TexSoup that \def\name{}

    This function parses the text to add braces if needed
    \def\name{} --> \def{\name}{}

    https://github.com/alvinwan/TexSoup/issues/131
    '''
    search_def_gdef = re.compile(r'(\\.{0,1}def)(.[\w]*)({.*})')
    try:
        pre, name, content = search_def_gdef.findall(text)[0]
        if name.startswith('{') or name.startswith('\\'):
            if name.startswith('{') and name.endswith('}'):
                text_ = ''.join([pre, name, content])
            else:
                text_ = ''.join([pre, '{', name, '}', content])
            return text_
        else:
            return text
    except IndexError:
        return text

def get_macros_names(macros: Sequence[str]) -> Sequence[str]:
    """ return a list of names from the macros newcommand definitions """

    def ignore_error(func, extype=Exception):
        """ run func catching exceptions to ignore """
        def deco(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except extype:
                pass
        return deco

    def get_name(node):
        """Get the macro name"""
        return node.newcommand.args[0].contents[0].name

    res = [ignore_error(TexSoup)(k) for k in macros]

    return drop_none_from_list(
        [ignore_error(get_name)(mk) for mk in res if mk ])


def force_macros_mathmode(text: str, macros: Sequence[str]) -> str:
    """ Make sure that detected macros are in math mode. They sometimes are not"""
    if macros is None:
        return text
    macros_names = get_macros_names(macros)
    text_ = text[:]
    for mk in macros_names:
        text_ = re.compile(r'(?:(?<=[^$]))\\' + mk).sub(r'$\\' + mk + '$', text_)
    return text_

class LatexDocument:
    """ Handles the latex document interface.

    Allows to extract title, authors, figures, abstract

    :param folder: folder containing the document
    :param main_file: name of the main document
    :param content: the document content from TexSoup
    :param title: the title of the paper
    :param authors: the authors of the paper
    :param comments: the comments of the paper
    :param abstract: the abstract of the paper
    """
    def __init__(self, folder: str):
        self.main_file = find_main_doc(folder)
        self.folder = folder
        self._figures = None
        self._abstract = None
        self._title = None
        self._authors = None
        self.comment = None
        self.macros = None

        with open(self.main_file, 'r') as fin:
            main_tex = fin.read()
        self.content = TexSoup(self._clean_source(main_tex))
        self.macros = self.retrieve_latex_macros()

    def _clean_source(self, source: str) -> str:
        """ Clean the source of the document

        :param source: the source to clean
        :return: cleaned source
        """
        import re
        source = clear_latex_comments(source).replace('$$', '$')
        self.source = source[:]
        source = '\n'.join([fix_def_command(k) for k in source.splitlines() if k])
        source = re.sub('\s+', ' ', source)
        source = re.sub('\n+', '\n', source)
        source = re.sub('\s+\n', '\n', source)
        source = re.sub(r'{}', ' ', source)   #empty commands
        # often missing spaces around $.
        source = re.sub(r'(?<=[^\$])\$(?=[^\$])', ' $ ', source)
        # \\s used to force spaces.
        source = re.sub(r'\\\s', ' ', source)
        return source

    def retrieve_latex_macros(self) -> Sequence[str]:
        """Get the macros defined in the document """

        keys = (r'providecommand', r'command', r'newcommand',
                r'renewcommand', r'def', r'gdef')

        identified_macros = []
        for command_k in keys:
            identified_macros.append('\n'.join(map(str, self.content.find_all(command_k))))

        macros = '\n'.join(identified_macros)\
                    .replace('provide', 'new')\
                    .replace('gdef', 'newcommand')\
                    .replace('def', 'newcommand')\
                    .replace('renewcommand', 'newcommand')\
                    .replace(' $ ', '')\
                    .replace('$', '')

        # some may be important to bypass
        required_macros = '\n'.join(
            [r'$\newcommand{\ensuremath}{}$',
             r'$\newcommand{\xspace}{}$',
             r'$\newcommand{\object}[1]{\texttt{#1}}$',
             r"$\newcommand{\farcs}{{.}''}$",
             r"$\newcommand{\farcm}{{.}'}$",
             r"$\newcommand{\arcsec}{''}$",
             r"$\newcommand{\arcmin}{'}$",
            ])

        macros_text = '\n'.join(['$' + k + '$' for k in macros.splitlines() if k])

        return (required_macros + '\n' + macros_text).splitlines()

    def get_all_figures(self) -> Sequence[LatexFigure]:
        """ Retrieve all figures (num, images, caption, label) from a document

        :param content: the document content
        :return: sequence of LatexFigure objects
        """
        figures = self.content.find_all('figure') + self.content.find_all('figure*')
        folder = self.folder
        data = []
        for num, fig in enumerate(figures, 1):
            num = num
            images = [f"{folder}/" + k.text[-1] for k in fig.find_all('includegraphics')]
            try:
                caps = fig.find_all('caption')
                caption = []
                for cap in caps:
                    captxt = ''.join(map(str, cap.contents))
                    """
                    textbf = [''.join(str(k)) for k in cap.find_all('textbf')]
                    for key in textbf:
                        try:
                            captxt = re.sub(r"\\textbf\{" + re.escape(key) + r"\}", f"**{key:s}**", captxt)
                        except:
                            pass
                    textit = [''.join(str(k)) for k in cap.find_all('textit')]
                    for key in textbf:
                        try:
                            captxt = re.sub(r"\\textit\{" + re.escape(key) + r"\}", f"_{key:s}_", captxt)
                        except:
                            pass
                    """
                    caption.append(captxt)
                caption = ''.join(caption).replace('~', ' ')
            except IndexError:
                # Sometimes no captions (multipage figures)
                caption = "- Incorrectly specified caption -"
            try:
                label = [''.join(k.text) for k in fig.find_all('label')][0]
            except IndexError:
                label = ''
            fig = LatexFigure(num=num, images=images, caption=caption, label=label)
            data.append(fig)
        return data

    @property
    def figures(self) -> Sequence[LatexFigure]:
        """ All figures from the paper """
        if not self._figures:
            self._figures = self.get_all_figures()
        return self._figures

    def get_abstract(self) -> str:
        """ Extract abstract from document """
        abstract = self.content.find_all('abstract')[0]
        abstract = [str(k).strip() for k in abstract if str(k)]
        abstract = [l.replace('~', ' ').replace('\n', '').strip() for l in abstract if l[0] != '%']
        abstract = ''.join(abstract)
        return abstract

    @property
    def abstract(self) -> str:
        """ All figures from the paper """
        if not self._abstract:
            self._abstract = self.get_abstract()
        return self._abstract

    def get_title(self) -> str:
        """ Extract document's title """
        title = ''.join(self.content.find_all('title')[0].text)
        try:
            subtitle = ''.join(r.find_all('subtitle')[0].text)
            return ': '.join([title, subtitle])
        except:
            return title

    @property
    def title(self) -> str:
        """ All figures from the paper """
        if not self._title:
            self._title = self.get_title()
        return self._title

    def get_authors(self) -> Sequence[str]:
        """ Get list of authors """
        authors = []
        author_decl = self.content.find_all('author')
        # parsing multi-author commands (new journal styles)
        if len(author_decl) > 1:
            orcid_search = re.compile('[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}')
            for ak in author_decl:
                if orcid_search.search(ak[0]):
                    authors.append(''.join(ak[1:]))
                else:
                    authors.append(''.join(ak))
        else:
            # The following is buggy: does not work for \author{name affil, name2 affil2, ...}
            for k in author_decl[0]:
                if str(k)[0] != '\\':
                    authors.append(str(k).replace('~', ' ')\
                                         .replace(',', '')\
                                         .strip())
        return authors

    @property
    def authors(self) -> str:
        """ All figures from the paper """
        if not self._authors:
            self._authors = self.get_authors()
        return self._authors

    @property
    def short_authors(self, nmin: int = 4) -> Sequence[str]:
        """ Make a short author list if there are more authors than nmin
        This means <first author> et al., -- incl <list of hihglighted authors>

        :param authors: the list of authors
        :param nmin: the minimum number of authors to switch to short representation
        :return: the list of authors
        """
        authors = self.authors
        if len(authors) <= nmin:
            return authors
        # short list means first author, et al. -- incl. [hl_list]
        short_list = [authors[0]] + [k for k in authors[1:] if '<mark>' in k]
        if len(short_list) < len(authors):
            if short_list[1:]:
                short_list = [short_list[0] + ', et al. -- incl.'] + short_list[1:]
            else:
                short_list = [short_list[0] + ', et al.']
        return short_list

    def select_most_cited_figures(self, N: int = 4):
        """ Finds the number of references to each figure and select the N most cited ones

        :param N: number of figures to select
        :return: list of selected figures
        """
        return select_most_cited_figures(self.figures, self.content)

    def highlight_authors_in_list(self, hl_list: Sequence[str]):
        """ highlight all authors of the paper that match `lst` entries

        :param hl_list: list of authors to highlight
        """
        new_authors = []
        for author in self.authors:
            found = False
            for hl in hl_list:
                if hl in author:
                    new_authors.append(f"<mark>{author}</mark>")
                    found = True
                    break
            if not found:
                new_authors.append(f"{author}")
        self._authors = new_authors

    def get_macros_markdown_text(self, show_errors: bool = False) -> str:
        """ Construct the Markdown object of the macros """
        macros_text = '\n'.join(self.macros)
        if show_errors:
            macros_text = (
                '<div class="macros" style="background:yellow;visibility:visible;">\n' +
                macros_text +
                '</div>')
        else:
            macros_text = (
                '<div class="macros" style="visibility:hidden;">\n' +
                macros_text +
                '</div>')

        return macros_text

    def generate_markdown_text(self, with_figures:bool = True) -> str:
        """ Generate the markdown summary

        :param with_figures: if True, the figures are included in the summary
        :return: markdown text
        """
        latex_abstract = self.abstract
        latex_title = self.title
        latex_authors = self.short_authors
        joined_latex_authors = ', '.join(latex_authors)
        selected_latex_figures = self.select_most_cited_figures()

        if self.comment:
            joined_latex_authors = '\n\n'.join([self.comment, joined_latex_authors])

        text = f"""# {latex_title}\n\n {joined_latex_authors} \n\n **Abstract:** {latex_abstract}"""
        if with_figures:
            figures = [k.generate_markdown_text().replace('|---------|\n', '')
                       for k in selected_latex_figures]
            # encapsulate into divs
            figures_ = []
            for (e, fk) in enumerate(figures, 1):
                figures_.extend([f'<div id="fig{e:d}">\n', fk, '\n</div>'])
            figures_ = '\n'.join(figures_)
            text = text + '\n' + figures_
        macros_md = self.get_macros_markdown_text() + '\n\n'
        return  macros_md + force_macros_mathmode(text, self.macros)

    def _repr_markdown_(self):
        if Markdown is None:
            raise ImportError('could not import `IPython.display.Markdown`')
        return Markdown(self.generate_markdown_text())._repr_markdown_()