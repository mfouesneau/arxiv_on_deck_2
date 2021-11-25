"""
Interface to Arxiv Vanity

https://www.arxiv-vanity.com/

access a paper through the following URL:
https://www.arxiv-vanity.com/papers/{arxiv_id}

If the paper is not already stored, it will be processed.
"""

import requests
from requests.exceptions import HTTPError
from io import BytesIO
from bs4 import BeautifulSoup
from IPython.display import Markdown
from typing import Sequence
import time


def collect_summary_information(paper_id: str,
                                content_requirements: callable = None) -> dict:
    """ Extract necessary information from the vanity webpage

    :raises HTTPError: If vanity is not accessible
    :raises RuntimeError: if the content_requirements returns False for this paper
    :return: a dictionary with the following keys: (title, authors, abstract, paper_id, url, figures, and the soup object)
    """

    url = f"https://www.arxiv-vanity.com/papers/{paper_id:s}/"

    # Get the paper data (wait if necessary)
    retrieved = False
    while(not retrieved):
        response = requests.get(url)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if 'This paper is rendering!' in response.content.decode():
                print("We need to wait for the paper to be ready on Vanity...\n",
                    url)
                for count in reversed(range(1, 31)):
                    print("Retry in {0:02d} seconds...".format(count), end='\r')
                    time.sleep(1)
            if "failed to render" in response.content.decode():
                raise HTTPError("Arxiv-Vanity failed to render the paper.")
            else:
                raise e
        retrieved = True
    soup = BeautifulSoup(response.content, 'html.parser')

    if content_requirements:
        if not content_requirements(response.content.decode()):
            raise RuntimeError("Paper does not satisfy the requirements.")

    # Get title
    title = soup.find_all('h1', attrs={'class': 'ltx_title'})[0]\
                .text.replace('\n', '')
    if 'thanks' in title:
        title = title.split('thanks')[0].replace('†', '')

    # Get authors
    authors = soup.find_all('span', {'class': "ltx_personname"})
    if len(authors) <= 1:
        # all authors in one entry
        authors = ''.join([str(k) for k in authors[0].contents if 'ltx' not in str(k)])\
                    .replace('\n', '')\
                    .split(',')
        authors = [k.strip() for k in authors]
    else:
        authors = [k.text.replace('\n', '').strip() for k in authors]
    authors = list(filter(lambda x: x, authors))  # keep non-empty

    # Get Abstract
    abstract = soup.find_all('div', {'class': "ltx_abstract"})[0].find_all('p')[0].text

    # Get figures
    figures = {}
    num = 0
    for fig in soup.find_all('figure', {"class": "ltx_figure"}):
        images = [k['src'] for k in fig.find_all('img')]
        captions = [k.text for k in fig.find_all('figcaption')]
        if not captions:
            continue
        caption_start_with = "Figure "
        caption = [k for k in captions
                    if k[:len(caption_start_with)] == caption_start_with]
        if not caption:
            continue
        num += 1
        figures[num] = (images if len(images) > 1 else images[0], caption[-1])

    return dict(title=title.strip(),
                authors=authors,
                abstract=abstract,
                paper_id=paper_id,
                url=url,
                figures=figures,
                soup=soup)


def select_most_cited_figures(content: dict, N: int = 3) -> Sequence:
    """ Finds the number of references to each figure and select the N most cited ones

    :param content: the content of the paper
    :param N: the number of figures to select
    :return: a list of N figures
    """
    # Find the number of references to each figure
    F_counts = {}
    soup = content['soup']
    references = [k for k in soup.find_all('a', {'class': 'ltx_ref'}) if k['title']]
    for ref in references:
        if '.' in ref['href']:
            data = ref['href'][1:].split('.')
            obj = data[1]
            # section, obj = ref['href'][1:].split('.')
            if obj[0] == 'F':
                F_counts[int(obj[1:])] = F_counts.get(int(obj[1:]), 0) + 1
    sorted_figures = sorted(F_counts.items(), key=lambda x: x[1], reverse=True)
    selected_figures = [content['figures'][k[0]] for k in sorted_figures[:N]]
    return selected_figures


def highlight_author(author_list: Sequence[str], author: str) -> Sequence[str]:
    """ Highlight a particular author in the list of authors

    :param author_list: the list of authors
    :param author: the author to highlight
    :return: the list of authors with the highlighted author
    """
    # TODO: make it a word matching regex
    new_lst = [f"<mark>{name}</mark>" if author in name else name for name in author_list]
    return new_lst


def highlight_authors_in_list(author_list: Sequence[str],
                              hl_list: Sequence[str]) -> Sequence[str]:
    """ highlight all authors of the paper that match `lst` entries

    :param author_list: the list of authors
    :param hl_list: the list of authors to highlight
    :return: the list of authors with the highlighted authors
    """
    new_authors = []
    for author in author_list:
        found = False
        for hl in hl_list:
            if hl in author:
                new_authors.append(f"<mark>{author}</mark>")
                found = True
                break
        if (not found):
            new_authors.append(f"{author}")

    return new_authors


def make_short_author_list(authors: Sequence[str],
                           nmin: int = 4) -> Sequence[str]:
    """ Make a short author list if there are more authors than nmin
    This means <first author> et al., -- incl <list of hihglighted authors>

    :param authors: the list of authors
    :param nmin: the minimum number of authors to switch to short representation
    :return: the list of authors
    """
    if len(authors) <= nmin:
        return authors
    # short list means first author, et al. -- incl. [hl_list]
    short_list = [authors[0]] + [k for k in authors[1:] if '<mark>' in k]
    if len(short_list) < len(authors):
        short_list = [short_list[0] + ', et al. -- incl.'] + short_list[1:]
    return short_list


def generate_markdown_text(content: dict) -> str:
    """Generate the summary markdown content

    :param content: the content of the paper
    :return: the markdown representation of the paper
    """
    title = content['title']
    paper_id = content['paper_id']
    url = content['url']
    abstract = content['abstract']
    authors = ', '.join(content['authors'])
    selected_figures = select_most_cited_figures(content)
    text = f"""# {title}

[![vanity](https://img.shields.io/badge/vanity-{paper_id}-f9f107.svg)]({url})
[![arXiv](https://img.shields.io/badge/arXiv-{paper_id}-b31b1b.svg)](https://arxiv.org/abs/{paper_id})

{authors}

**Abstract:** {abstract}

"""
    figure_text = []
    for num, (fig, caption) in enumerate(selected_figures, 1):
        if isinstance(fig, (list, tuple)) and (len(fig) > 1):
            # <img src="drawing.jpg" alt="drawing" width="200"/>
            width = 100 // len(fig)
            #current = '\n'.join(
            #    [f'![Fig{num:d}.{sub:d}]({figsub})' for sub, figsub in enumerate(fig, 1)]
            #)
            current = ''.join(
                [f'<img src="{figsub}" alt="Fig{num:d}.{sub:d}" width="{width}%"/>' for sub, figsub in enumerate(fig, 1)]
            ) + '\n'
        else:
            current = f"![Fig{num:d}]({fig})\n"
        current += f'\n{caption}'
        figure_text.append(current)
    return text + '\n\n'.join(figure_text)