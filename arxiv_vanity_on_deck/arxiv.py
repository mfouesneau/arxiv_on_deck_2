from typing import Sequence
from html.parser import HTMLParser
from urllib.request import urlopen


class ArXivPaper(object):
    """ Class that handles the interface to Arxiv website paper abstract """

    source = "https://arxiv.org/e-print/{identifier}"
    abstract = "https://arxiv.org/abs/{identifier}"

    def __init__(self, identifier: str = "", 
                 highlight_authors: Sequence[str] = None, 
                 appearedon: str = None):
        """ Initialize the data """
        self.identifier = identifier
        self.title = ""
        self._authors = []
        if highlight_authors is None:
            self.highlight_authors = []
        else:
            self.highlight_authors = highlight_authors
        self.comment = ""
        self.date = None
        self.appearedon = appearedon
        if len(self.identifier) > 0:
            self.get_abstract()

    @classmethod
    def from_identifier(cls, identifier: str):
        return cls(identifier.split(':')[-1]).get_abstract()

    @property
    def authors(self) -> str:
        authors = ", ".join(self._authors)
        if len(self.highlight_authors) > 0:
            for name in self.highlight_authors:
                if (name in authors):
                    authors = authors.replace(name, r'\hl{' + name + r'}')
        return authors

    @property
    def short_authors(self) -> str:
        if len(self.authors) < 5:
            return self.authors
        else:
            if any(name in self._authors[0] for name in self.highlight_authors):
                authors = r'\hl{' + self._authors[0] + r'}, et al.'
            else:
                authors = self._authors[0] + ", et al."
        if len(self.highlight_authors) > 0:
            incl_authors = []
            for name in self.highlight_authors:
                if name != self._authors[0]:
                    incl_authors.append(r'\hl{' + name + r'}')
            authors += '; incl. ' + ', '.join(incl_authors)
        return authors

    def __repr__(self):
        txt = """[{s.identifier:s}]: {s.title:s}\n\t{s.authors:s}"""
        return txt.format(s=self)

 
class ArxivListHTMLParser(HTMLParser):
    """ generates a list of Paper items by parsing the Arxiv new page """

    def __init__(self, *args, **kwargs):
        skip_replacements = kwargs.pop('skip_replacements', False)
        HTMLParser.__init__(self, *args, **kwargs)
        self.papers = []
        self.current_paper = None
        self._paper_item = False
        self._title_tag = False
        self._author_tag = False
        self.skip_replacements = skip_replacements
        self._skip = False
        self._date = kwargs.pop('appearedon', '')

    def handle_starttag(self, tag, attrs):
        # paper starts with a dt tag
        if (tag in ('dt') and not self._skip):
            if self.current_paper:
                self.papers.append(self.current_paper)
            self._paper_item = True
            self.current_paper = ArXivPaper(appearedon=self._date)

    def handle_endtag(self, tag):
        # paper ends with a /dd tag
        if tag in ('dd'):
            self._paper_item = False
        if tag in ('div',) and self._author_tag:
            self._author_tag = False
        if tag in ('div',) and self._title_tag:
            self._title_tag = False

    def handle_data(self, data):
        if data.strip() in (None, "", ','):
            return
        if 'replacements for' in data.lower():
            self._skip = (True & self.skip_replacements)
        if 'new submissions for' in data.lower():
            self._date = data.lower().replace('new submissions for', '')
        if self._paper_item:
            if 'arXiv:' in data:
                self.current_paper.identifier = data
            if self._title_tag:
                self.current_paper.title = data.replace('\n', '')
                self._title_tag = False
            if self._author_tag:
                self.current_paper._authors.append(data.replace('\n', ''))
                self._title_tag = False
            if 'Title:' in data:
                self._title_tag = True
            if 'Authors:' in data:
                self._author_tag = True


def get_new_papers(skip_replacements: bool = True) -> Sequence:
    """ retrieve the new list from the website
    Parameters
    ----------
    skip_replacements: bool
        set to skip parsing the replacements
    Returns
    -------
    papers: list(ArXivPaper)
        list of ArXivPaper objects
    """
    url = "https://arxiv.org/list/astro-ph/new"
    html = urlopen(url).read().decode('utf-8')

    parser = ArxivListHTMLParser(skip_replacements=skip_replacements)
    parser.feed(html)
    papers = parser.papers
    return papers


def filter_papers(papers: Sequence[ArXivPaper], 
                  fname_list: Sequence[str]) -> Sequence:
    """ Extract papers when an author match is found
    Parameters
    ----------
    papers: list(ArXivPaper)
        paper list
    fname_list: list(str)
        authors to search
    Returns
    -------
    keep: list(ArXivPaper)
        papers with matching author
    """
    keep = []
    matched_authors = []
    for paper in papers:
        paper.highlight_authors = []
        matches = [name for name in fname_list if ' ' + name in paper.authors]
        if matches:
            for author in paper._authors:
                for name in fname_list:
                    if name in author:
                        # TODO: add initials test
                        if (name == author.split()[-1]):
                            matched_authors.append((name, author, paper.identifier))
                            paper.highlight_authors.append(author)
                            keep.append(paper)
    return keep, matched_authors