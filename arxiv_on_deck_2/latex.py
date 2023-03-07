import os
from glob import glob
import warnings
import pathlib
from typing import Union, Sequence
import re
from TexSoup import TexSoup, TexNode
try:
    from IPython.display import Markdown
except ImportError:
    Markdown = None
from pdf2image import convert_from_path
from .arxiv_vanity import highlight_authors_in_list
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


def open_eps(filename, dpi=300.0):
    from PIL import Image
    # from PIL import EpsImagePlugin
    import math
    img = Image.open(filename)
    original = [float(d) for d in img.size]
    # scale = width / original[0] # calculated wrong height
    scale = dpi / 72.0            # this fixed it
    if dpi > 0:
        img.load(scale = math.ceil(scale))
    if scale != 1:
        img.thumbnail([round(scale * d) for d in original], Image.ANTIALIAS)
    return img


def convert_eps_to_image(fname: str) -> str:
    """ Convert image from EPS to png.

    The new image is stored with the original one

    :param fname: file to potentially convert
    """
    from PIL import Image
    rootname = fname.replace('.eps', '')
    open_eps(fname, dpi=500).save(f'{rootname}.png', format='PNG', dpi=[500, 500])
    return f'{rootname}.png'


def find_graphics(where: str, image: str, folder: str = '',
                  attempt_recover_extension: bool = True) -> str:
    """ Find graphics files for the figure if graphicspath provided """
    for wk in where:
        fname = os.path.join(folder, wk, image)
        if os.path.exists(fname):
            return fname
    if attempt_recover_extension:
        warnings.warn(LatexWarning(f'attempting recovering figure {image}'))
        for extension in ['.png', '.jpg', '.jpeg', '.pdf', '.eps']:
            for wk in where:
                fname = os.path.join(folder, wk, image + f'{extension}')
                if os.path.exists(fname):
                    return fname
    raise FileNotFoundError(f"Could not find figure {image}")
    
    
def tex2md(latex: str) -> str:
    """ Replace some obvious tex commands to their markdown equivalent """
    latex = re.sub(r"(\\emph{)(.*?)\}", r"*\2*", latex)
    latex = re.sub(r"({\\em)(.*?)\}", r"*\2*", latex)
    latex = re.sub(r"(\\textbf{)(.*?)\}", r"**\2**", latex)
    latex = re.sub(r"({\\bf)(.*?)\}", r"**\2**", latex)
    latex = re.sub(r"(\\textit{)(.*?)\}", r"_\2_", latex)
    latex = re.sub(r"({\\it)(.*?)\}", r"_\2_", latex)
    latex = re.sub(r"(\\textsc{)(.*?)\}", r"\2", latex)
    latex = re.sub(r"(\\section{)(.*?)\}", r"### \2", latex)
    latex = re.sub(r"(.*)\\begin{equation}", r"\n\n$$", latex)
    latex = re.sub(r"(.*)\\end{equation}", r"$$\n\n", latex)
    latex = re.sub(r"(.*)\\begin{itemize}\n", r"", latex)
    latex = re.sub(r"(.*)(\\end{itemize})\n", r"", latex)
    latex = re.sub(r"(.*)(\\centering)\n", r"", latex)
    latex = re.sub(r"\\label{.*?}", r"", latex)
    latex = re.sub(r"\\footnote{.*?}", r"", latex)
    latex = re.sub(r"(\\mbox{)(.*?)\}", r"$\2$", latex)
    latex = re.sub(r"(.*)\\item", r"*", latex)
    
    return(latex)


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
        self._check_eps_pdf_figure()

    def _check_images_path(self):
        """ Check if images are in the same folder as the document """
        images = self['images']
        if len(images) > 1:
            for image in images:
                if not os.path.exists(image):
                    raise FileNotFoundError(f"Could not find figure {image}")

    def _check_eps_pdf_figure(self):
        """ Check if PDF images and convert to PNG if needed """
        images = self['images']
        new_images = []
        for image in images:
            if image[-4:] == '.pdf':
                new_images.append(convert_pdf_to_image(image))
            elif image[-4:] == '.eps':
                new_images.append(convert_eps_to_image(image))
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

        return """{current}\n\n**Figure {num}. -** {caption} (*{label}*)""".format(
            current=current, caption=tex2md(self['caption']), label=self['label'], num=self['num'])

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
    r''' Fixing a small bug in TexSoup that \def\name{}

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


def inject_other_sources(maintex:str ,
                         texfiles: Sequence[str],
                         verbose: bool = False):
    """ replace input and include commands by the content of the sub-files """

    # find all include and input commands
    include_regex = re.compile(r'(?:(?<=[^$]))\\(?:input|include)\{(.*?)\}')
    # important to start from the end to avoid breaking the span indices
    externals = reversed(list(include_regex.finditer(maintex)))

    # the following matches the full filenames without extensions
    for match in externals:
        ext = match.group(1)
        ext_ = os.path.splitext(os.path.basename(ext))[0]
        for subsource in texfiles:
            sub_ = os.path.splitext(os.path.basename(subsource))[0]
            if ext_ == sub_:
                if verbose:
                    warnings.warn(LatexWarning(f"Latex injecting: '{ext}' from '{subsource}'"))
                with open(subsource, 'r') as fsub:
                    subtext = fsub.read()
                s, e = match.span()
                maintex = ''.join([
                    maintex[:s],
                    '% ', maintex[s: e], ' % -- REPLACED BY LATEX INJECTION -- \n',
                    subtext,
                    maintex[e:]])
    return maintex


def get_content_per_section(source: str, flexible:bool = True, verbose: bool = True) -> Sequence:
    """ Find problematic portions of the document and attempt to skip them """
    import re
    from itertools import chain

    # Checking header
    begin_doc = next(re.finditer(r'\\begin\{document\}', source)).span()[1]

    # Check the text per section until the end.
    # Do not stop and try them all.

    problematic_text = []

    sections = ([(0, begin_doc, 'header')] +
                [(g.span()[0], g.span()[1], g.group()) for g in re.finditer(r'\\section\{.*\}', source)] +
                [(g.span()[0], g.span()[1], g.group()) for g in re.finditer(r'\\begin\{appendix\}', source)] +
                [(len(source), len(source), 'end')]
            )

    sections = sorted(sections, key=lambda x: x[0])

    prev_pos, prev_name = (0, 'header')
    parsed = []

    for span, span_end, name in sections:
        if span - prev_pos <= 0:
            continue
        text = source[prev_pos:span]
        if prev_pos > begin_doc:
            text = r"\n\begin{document}" + text + r"\n\end{document}"
        else:
            text = text + r"\n\end{document}"
        try:
            parsed.append(TexSoup(text, tolerance=int(flexible)))  # allow not ending env
            if verbose:
                print(f"✔ → {prev_pos}:{prev_name}\n  ↳ {span}:{name}")

            prev_pos = span
            prev_name = name
        except:
            if verbose:
                print(f"✘ → {prev_pos}:{prev_name}\n  ↳ {span}:{name}")
            problematic_text.append((prev_pos, source[prev_pos:span]))
            prev_pos = span
            prev_name = name

    final = parsed[0]
    final.append(*list(chain(*[bk.expr._contents for bk in parsed[1:]])))
    return final, parsed, problematic_text



def get_content(source: str, flexible:bool = True, verbose:bool = False) -> TexNode:
    # flexible=True, current_attempt=0, max_attempt=10) -> str:
    """ get soup to parse the source and try to recover if something goes wrong.

    As we do not need the exact text throughout the paper, we can try to isolate potential error sections.
    The following attempts to remove the line that triggers an error.
    """
    try:
        return TexSoup(source, tolerance=int(flexible))
    except:
        warnings.warn(LatexWarning(f"Error parsing the document directly. Trying to recover."))
        return get_content_per_section(source, flexible=flexible, verbose=verbose)[0]
    """
    except EOFError as error:
        # End of document error. split around the offending line and try again
        if (current_attempt >= max_attempt) or not flexible:
            raise error
        offset = int(re.findall(r'\[.* Off.* ([0-9]*)\]', str(error))[0])
        newsource = source.splitlines()
        a = TexSoup('\n'.join(newsource[:64]) + '\n\end{document}')
        b = TexSoup('\n'.join(newsource[65:]))  # no need to begin{document}
        a.append(*b)
        return a
    except TypeError as e:
        error = e
        offset = int(re.findall(r'\[.* Off.* ([0-9]*)\]', str(error))[0])
        error_at_line = source[:offset].count('\n')
        warnings.warn(LatexWarning(f"error at line {error_at_line:,d}"))
        if not flexible:
            raise e

        newsource = source.splitlines()
        newsource = newsource[:error_at_line] + newsource[error_at_line + 1:]
        return get_content('\n'.join(newsource),
                           flexible=current_attempt < max_attempt,
                           current_attempt= current_attempt + 1,
                           max_attempt=max_attempt)
        """
        

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
    def __init__(self, folder: str, validation: callable = None, debug: bool = False):
        self.main_file = find_main_doc(folder)
        self.folder = folder
        self._figures = None
        self._abstract = None
        self._title = None
        self._authors = None
        self.comment = None
        self.macros = None
        self.graphicspath = None

        with open(self.main_file, 'r') as fin:
            source = fin.read()
        source = inject_other_sources(source, self.get_texfiles(), verbose=True)
        if validation is not None:
            validation(source)
        source = self._clean_source(source)
        # self.content = TexSoup(source)
        try:
            content = get_content(source, flexible=True, verbose=True)
            self._load_content(content)
        except Exception as e:
            if not debug:
                raise e
            else:
                print(e)
        self.source = source

    def _load_content(self, content):
        self.content = content
        self.macros = self.retrieve_latex_macros()
        self.graphicspath = self.get_graphicspath()

    def get_graphicspath(self) -> Sequence[str]:
        """Retrieve the graphicspath if declared"""
        # list of directories in {}
        try:
            where = [str(k.string) for k in self.content.find_all('graphicspath')[0].contents]
        except:
            where = ['./']

        return [os.path.join(self.folder, k) for k in where]

    def get_texfiles(self):
        """ returns all tex files in the folder (and subfolders) """
        folder = self.folder
        return [str(k) for k in pathlib.Path(f"{folder}").glob("**/*.tex")]

    def _clean_source(self, source: str) -> str:
        """ Clean the source of the document

        :param source: the source to clean
        :return: cleaned source
        """
        import re
        source = clear_latex_comments(source).replace('$$', '')\
                                             .replace('``', '"')\
                                             .replace("''", '"')
        source = '\n'.join([fix_def_command(k) for k in source.splitlines() if k])
        source = re.sub(r'\$\$', r'', source)
        # source = re.sub(r'\s\s+', ' ', source)
        source = re.sub(r'\n\n+', r'\n', source)
        # source = re.sub(r'\n+', r'\n', source)
        source = re.sub(r'\s+\n', r'\n', source)
        source = re.sub(r'\{\}', ' ', source)   #empty commands
        # some people play with $$ within equations...
        # replace by \[ ... \] and remove isolated $$
        # source = re.sub(r'(?P<env>(\${2}))(.*)(?P=env)', r'\\[\g<3>\\]', source)

        # source = re.sub(r'(?<!(\s|\^))\$\$(?!(\s|$))', '', source)
        # often missing spaces around $.
        # source = re.sub(r'(?<=[^\$])\$(?=[^\$])', ' $ ', source)
        # \\s and \\, used to force spaces.
        source = re.sub(r'\\\s', ' ', source)
        source = re.sub(r'\\,', ' ', source)
        # some varied graphics commands that should die.
        source = re.sub(r'\\plotone\{(.*)\}', r'\\includegraphics{\g<1>}', source)
        source = re.sub(r'\\plottwo\{(.*)\}\{(.*)\}', r'\\includegraphics{\g<1>}\\includegraphics{\g<2>}', source)

        # special characters
        which = [
            (r'\\~{n}', r'ñ'),
            (r'\\~{o}', r'õ'),
            (r'\\~{a}', r'ã'),
            (r"\\`{a}", r'à'),
            (r"\\`{e}", r'è'),
            (r"\\`{i}", r'ì'),
            (r"\\`{o}", r'ò'),
            (r"\\`{u}", r'ù'),
            (r"\\'{a}", r'á'),
            (r"\\'{e}", r'é'),
            (r"\\'{i}", r'í'),
            (r"\\'{o}", r'ó'),
            (r"\\'{u}", r'ú'),
            (r'\\"{u}', r'ü'),
            (r'\\"{o}', r'ö'),
            (r'\\"{a}', r'ä'),
            (r'\\"{e}', r'ë'),
            (r'\\"{i}', r'ï'),
            (r'\\^{i}', r'î'),
            (r'\\^{e}', r'ê'),
            (r'\\c{c}', r'ç'),
            (r"\\'{\\i}", r'í'),
            (r"\\`{\\i}", r'ì'),
            (r"\\AA", r'Å'),
        ]
        
        # add those without the {} 
        which = which + [(k.replace('{', '').replace('}', ''), v) for k, v in which]
        # add capital letters too
        which = which + [(k.upper(), v.upper()) for k, v in which]
        
        for from_, to_ in which:
            source = re.sub(from_, to_, source)
        self.source = source
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
             r"$\newcommand{\ion}[2]{#1#2}$",
             r"$\newcommand{\textsc}[1]{\textrm{#1}}$",
             r"$\newcommand{\hl}[1]{\textrm{#1}}$",
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
            # num = num
            # images = [f"{folder}/" + k.text[-1] for k in fig.find_all('includegraphics')]
            images = [find_graphics(self.graphicspath, k.text[-1])
                      for k in fig.find_all('includegraphics')]
            try:
                caps = fig.find_all('caption')
                caption = []
                for cap in caps:
                    captxt = ''.join(map(str, cap.contents))
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
        try:
            abstract = self.content.find_all('abstract')[0]
            abstract = [str(k).strip() for k in abstract if str(k)]
            abstract = [l.replace('~', ' ').replace('\n', '').strip() for l in abstract if l[0] != '%']
            abstract = ' '.join(abstract)
            return abstract
        except Exception as e:
            warnings.warn(LatexWarning(f"Could not extract abstract from {self.main_file}"))
            return ""

    @property
    def abstract(self) -> str:
        """ All figures from the paper """
        if not self._abstract:
            self._abstract = self.get_abstract()
        return self._abstract

    def get_title(self) -> str:
        """ Extract document's title """
        # title = ''.join(self.content.find_all('title')[0].contents[-1])
        title = self.content.find_all('title')[0]
        # remove BracketGroup (command options)
        title = [arg.string for arg in title.expr.args if arg.name != "BracketGroup"][0]
        title = ''.join(str(k) for k in title if 'thanks' not in str(k))
        
        try:
            # subtitle = ''.join(self.content.find_all('subtitle')[0].contents[-1])
            subtitle = [arg.string for arg in self.content.find_all('subtitle')[0] if arg.name != "BracketGroup"][0]
            subtitle = ''.join(str(k) for k in subtitle if 'thanks' not in str(k))
            text = ': '.join([title, subtitle]).replace('\n', '')
        except:
            text = title.replace('\n', '')
        return text.replace('~', ' ')

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
            orcid_search = re.compile('[0-9X]{4}-[0-9X]{4}-[0-9X]{4}-[0-9X]{4}')
            for ak in author_decl:
                opts = ak.contents[0]
                if orcid_search.search(opts):
                    authors.append(''.join(map(str, ak.contents[1:])))
                else:
                    try:
                        authors.append(''.join(ak.string))
                    except: # multiple arguments
                        authors.append(''.join(map(str, ak.contents[1:])))


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

    def highlight_authors_in_list(self, hl_list: Sequence[str], verbose: bool = False):
        """ highlight all authors of the paper that match `lst` entries

        :param hl_list: list of authors to highlight
        :param verbose: display matching information if set
        """
        self._authors = highlight_authors_in_list(self.authors, hl_list, verbose=verbose)

    def get_macros_markdown_text(self) -> str:
        """ Construct the Markdown object of the macros """
        macros_text = (
            '<div class="macros" style="visibility:hidden;">\n' +
            '\n'.join(self.macros) +
            '</div>')

        return macros_text

    def generate_markdown_text(self, with_figures:bool = True) -> str:
        """ Generate the markdown summary

        :param with_figures: if True, the figures are included in the summary
        :return: markdown text
        """
        latex_abstract = tex2md(self.abstract)
        latex_title = tex2md(self.title.replace('~', ' '))
        latex_authors = self.short_authors
        joined_latex_authors = ', '.join(latex_authors)
        selected_latex_figures = self.select_most_cited_figures()
        macros_md = self.get_macros_markdown_text() + '\n\n'

        text = f"""{macros_md}\n\n<div id="title">\n\n# {latex_title:s}\n\n</div>\n"""
        if self.comment:
            text += f"""<div id="comments">\n\n{self.comment:s}\n\n</div>\n"""
        text += f"""<div id="authors">\n\n{joined_latex_authors:s}\n\n</div>\n"""
        text += f"""<div id="abstract">\n\n**Abstract:** {latex_abstract:s}\n\n</div>\n"""

        if with_figures:
            figures = [k.generate_markdown_text().replace('|---------|\n', '')
                       for k in selected_latex_figures]
            # encapsulate into divs
            figures_ = []
            for (e, fk) in enumerate(figures, 1):
                figures_.extend([f'<div id="div_fig{e:d}">\n', fk, '\n</div>'])
            figures_ = '\n'.join(figures_)
            text = text + '\n' + force_macros_mathmode(figures_, self.macros)
        return  macros_md + text

    def _repr_markdown_(self):
        if Markdown is None:
            raise ImportError('could not import `IPython.display.Markdown`')
        return Markdown(self.generate_markdown_text())._repr_markdown_()
