""" How to deal with ArXiv and getting papers' information and sources """

import tarfile
import os
import shutil
import requests
from urllib.request import urlopen
from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import Sequence
from datetime import datetime
try:
    from IPython.display import Markdown
except ImportError:
    Markdown = None


class ArxivPaper(dict):
    """ Paper representation using ArXiv information

    A dictionary like structure that contains:

    - identifier: the arxiv identification number
    - title: the title of the paper
    - authors: the authors of the paper
    - comments: the comments of the paper
    - abstract: the abstract of the paper
    """
    def __init__(self, **paper_data):
        super().__init__(paper_data)

    @property
    def short_authors(self, nmin: int = 4) -> Sequence[str]:
        """ Make a short author list if there are more authors than nmin
        This means <first author> et al., -- incl <list of hihglighted authors>

        :param authors: the list of authors
        :param nmin: the minimum number of authors to switch to short representation
        :return: the list of authors
        """
        authors = self['authors']
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

    @classmethod
    def from_bs4_tags(cls, dt: Tag, dd: Tag):
        """ extract paper information from its pair of tags

        :param dt: the tag of the title
        :param dd: the tag of the description
        :return: the paper object
        """
        identifier = dt.find("a", attrs={'title':"Abstract"}).text
        authors = [k.text.strip() for k in dd.find('div', attrs={'class':"list-authors"}).find_all('a')]
        abstract = dd.find('p')\
                     .text\
                     .replace('\n', ' ')
        title = dd.find('div', {'class': "list-title"})\
                  .text.replace('\n', '')\
                  .replace('Title:', '')\
                  .strip()
        try:
            comments = dd.find('div', {'class': "list-comments"})\
                         .text\
                         .replace('\n', '')\
                         .replace('Comments:', '')\
                         .strip()
        except AttributeError:
            comments = ""

        date = ""

        data = dict(identifier=identifier,
                    authors=authors,
                    abstract=abstract,
                    title=title,
                    date = date,
                    comments=comments)
        return ArxivPaper(**data)

    def generate_markdown_text(self) -> str:
        """ Generate the markdown text of this paper

        :return: the markdown text summary of the paper
        """
        joined_authors = ', '.join(self.short_authors)
        return """
|||
|---:|:---|
| [![arXiv](https://img.shields.io/badge/arXiv-{identifier}-b31b1b.svg)](https://arxiv.org/abs/{identifier}) | **{title}**  |
|| {joined_authors} |
|*Appeared on*| *{date}*|
|*Comments*| *{comments}*|
|**Abstract**| {abstract}|""".format(joined_authors=joined_authors, **self)

    def _repr_markdown_(self):
        if Markdown is None:
            raise ImportError('could not import `IPython.display.Markdown`')
        return Markdown(self.generate_markdown_text())._repr_markdown_()

    def __repr__(self):
        joined_authors = ', '.join(self.short_authors)
        txt = """[{identifier}] {title}\n\t{joined_authors}"""
        return txt.format(joined_authors=joined_authors, **self)


def get_new_papers() -> Sequence[ArxivPaper]:
    """retrieve the new list from the website.

    :return: list of ArXivPaper objects
    """
    url = "https://arxiv.org/list/astro-ph/new"

    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    date = soup.find_all('div', {'class': 'list-dateline'})[0].text.replace('\n', '').split(',')[-1].strip()
    date = str(datetime.strptime(date, '%d %b %y').date())
    r = soup.find_all('dl')[0].find_all(['dt', 'dd'])
    new_papers = [ArxivPaper.from_bs4_tags(dt, dd) for dt, dd in zip(r[::2], r[1::2])]
    for paper in new_papers:
        paper['date'] = date
    return new_papers


def get_paper_from_identifier(paper_identifier: str) -> ArxivPaper:
    """ Retrieve a paper from Arxiv using its identifier

    :param paper_identifier: arxiv identifier of the paper
    :return: Paper object
    """
    abstract_url = f"https://arxiv.org/abs/{paper_identifier}"
    response = requests.get(abstract_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')


    title = soup.find('h1', {'class': "title"})\
                .text.replace('\n', '')\
                .replace('Title:', '')\
                .strip()

    authors = [k.text.strip() for k in soup.find('div', attrs={'class':"authors"}).find_all('a')]

    abstract = soup.find('blockquote', {'class': 'abstract'})\
                   .text.replace('\n', '')\
                   .replace('Abstract:', '')\
                   .strip()

    comments = soup.find('td', {'class': 'comments'})\
                   .text.replace('\n', '')\
                   .strip()

    date = soup.find('div', {'class': "dateline"})\
                    .text.replace('\n', '')\
                    .replace('[Submitted on', '').replace(']', '')\
                    .strip()
    date = str(datetime.strptime(date, '%d %b %Y').date())

    data = dict(identifier=paper_identifier,
                authors=authors,
                abstract=abstract,
                title=title,
                date=date,
                comments=comments)

    return ArxivPaper(**data)


def retrieve_document_source(identifier: str, directory: str) -> str:
    """ Retrieve document source tarball and extract it.

    :param identifier: Paper identification number from Arxiv
    :param directory: where to store the extracted files
    :return: directory in which the data was extracted
    """
    where = f"https://arxiv.org/e-print/{identifier}"
    print("Retrieving document from ", where)
    tar = tarfile.open(mode='r|gz', fileobj=urlopen(where))

    if os.path.isdir(directory):
        shutil.rmtree(directory)
    print(f"extracting tarball to {directory:s}...", end='')
    tar.extractall(directory)
    print(" done.")
    return directory


def get_markdown_badge(identifier: str) -> str:
    """ Generate the markdown badge for a paper

    :param identifier: arxiv identifier of the paper
    :return: markdown badge
    """
    return f"[![arXiv](https://img.shields.io/badge/arXiv-{identifier}-b31b1b.svg)](https://arxiv.org/abs/{identifier})"