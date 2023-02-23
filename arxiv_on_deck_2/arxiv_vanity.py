"""
Interface to Arxiv Vanity

https://www.arxiv-vanity.com/

access a paper through the following URL:
https://www.arxiv-vanity.com/papers/{arxiv_id}

If the paper is not already stored, it will be processed.
"""

import requests
import re
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup
from typing import Sequence
import time


def _parse_response(paper_id: str,
                    response: requests.Response,
                    content_requirements: callable = None
                   ) -> dict:
    """
    :param paper_id: paper identifier
    :param response: response from arxiv vanity
    :return: a dictionary with the following keys: (title, authors, abstract, paper_id, url, figures, and the soup object)
    """

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
        if images:
            num += 1
            figures[num] = (images if len(images) > 1 else images[0], caption[-1])

    url = f"https://www.arxiv-vanity.com/papers/{paper_id:s}/"

    return dict(title=title.strip(),
                authors=authors,
                abstract=abstract,
                paper_id=paper_id,
                url=url,
                figures=figures,
                soup=soup)


def collect_summary_information(identifiers: Sequence[str],
                                content_requirements: callable = None,
                                wait: int = 10) -> Sequence[dict]:
    """ Extract necessary information from the vanity webpage

    :param identifers: list of arxiv identifiers to attempt to retrieve
    :param content_requirement: filter function that returns False if the paper does not meet the requirements
    :param wait: how many seconds to wait between retries.

    :return: a dictionary with the following keys: (title, authors, abstract, paper_id, url, figures, and the soup object)
    """

    url = "https://www.arxiv-vanity.com/papers/{paper_id:s}/"

    if not isinstance(identifiers, (list, tuple, set)):
        return collect_summary_information([identifiers], content_requirements, wait)

    # Queue all requests at once, giving vanity more time to process
    print("starting all requests in the queue")
    queue = [(paper_id, requests.get(url.format(paper_id=paper_id))) for paper_id in identifiers]
    print("... requests sent.")
    errors = {}
    retrieved = {}


    while ((len(errors) + len(retrieved)) < len(identifiers)):
        for paper_id, response in queue:
            # print(f"requesting status of {paper_id}")

            # skip if already obtained
            if paper_id in retrieved:
                continue

            try:
                    response.raise_for_status()
                    retrieved[paper_id] = response
                    # print(f"{paper_id} retrieved")
            except requests.exceptions.HTTPError as e:
                    if 'This paper is rendering!' in response.content.decode():
                        # print("We need to wait for the paper to be ready on Vanity... (remains in queue)\n", url)
                        pass
                    if "failed to render" in response.content.decode():
                        errors[paper_id] = (paper_id, response, "Arxiv-Vanity failed to render the paper.")
                        # raise HTTPError("Arxiv-Vanity failed to render the paper.")
                    if "doesn't have LaTeX source code" in response.content.decode():
                        errors[paper_id] = (response, "The paper does not have LaTeX source code.")
                        # raise RuntimeError("The paper does not have LaTeX source code.")
                    if "Service Unavailable" in e.response.reason:
                        # print(paper_id, response, "Communication error. Will retry.")
                        pass
                    if "Internal Server Error" in e.response.reason:
                        #print(paper_id, response, "Internal Server Error. Will retry.")
                        pass
                    if "Not Found" in e.response.reason:
                        # print(paper_id, response, "Internal Server Error. Will retry.")
                        pass
                    else:
                        errors[paper_id] = (response, e)
                    #print(paper_id + ":" + str(errors.get(paper_id, None)))

        print("Identifiers {0:,d}, Retrieved {1:,d} papers ({2:,d} generated errors)".format(len(identifiers), len(retrieved), len(errors)))
        for count in reversed(range(1, wait)):
                    print("Not all papers were ready. Retry in {0:02d} seconds...".format(count), end='\r', flush=True)

                    time.sleep(1)
        print("Not all papers were ready. Retrying...".format(count), end='\r', flush=True)
    print("\ndone.\n", "Identifiers {0:,d}, Retrieved {1:,d} papers ({2:,d} generated errors)".format(len(identifiers), len(retrieved), len(errors)))

    contents = []
    for (paper_id, response) in retrieved.items():
        try:
            contents.append(_parse_response(paper_id, response, content_requirements))
        except HTTPError as httpe:
            print(f"Error with paper {paper_id}... ({httpe})")
        except RuntimeError as re:
            print(f"Not an MPIA paper {paper_id}... ({re})")

    return contents


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


def author_match(author: str, hl_list: Sequence[str], verbose=False) -> Sequence[str]:
    """ Matching author names with a family name reference list
    
    :param author: the author string to check
    :param hl_list: the list of reference authors to match
    :param verbose: prints matching results if set
    :return: the matching sequences or empty sequence if None
    """
    for hl in hl_list:
        match = re.findall(r"\b{:s}\b".format(hl), author, re.IGNORECASE)
        if hl in author:
            if verbose:
                print(author, hl, match)
            return match


def highlight_authors_in_list(author_list: Sequence[str], 
                              hl_list: Sequence[str], 
                              verbose: bool = False) -> Sequence[str]:
    """ highlight all authors of the paper that match `lst` entries

    :param author_list: the list of authors
    :param hl_list: the list of authors to highlight
    :param verbose: prints matching results if set
    :return: the list of authors with the highlighted authors
    """
    new_authors = []
    for author in author_list:
        match = author_match(author, hl_list)
        if match:
            new_authors.append(f"<mark>{author}</mark>")
        else:
            new_authors.append(f"{author}")
    return new_authors
  
def highlight_author(author_list: Sequence[str], author: str) -> Sequence[str]:
    """ Highlight a particular author in the list of authors

    :param author_list: the list of authors
    :param author: the author to highlight
    :return: the list of authors with the highlighted author
    """
    new_lst = [f"<mark>{name}</mark>" if author_match(name, author) else name for name in author_list]
    return new_lst


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

[![vanity](https://img.shields.io/badge/vanity-{paper_id}-f9f107.svg)](https://www.arxiv-vanity.com/papers/{paper_id})
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
                [f'<a href={figsub}><img src="{figsub}" alt="Fig{num:d}.{sub:d}" width="{width}%"/></a>' for sub, figsub in enumerate(fig, 1)]
            ) + '\n'
        else:
            current = f"![Fig{num:d}]({fig})\n"
        current += f'\n{caption}'
        figure_text.append(current)
    return text + '\n\n'.join(figure_text)


def get_arxiv_vanity_badge(identifier: str) -> str:
    """ Generate the markdown badge for a paper

    :param identifier: arxiv identifier of the paper
    :return: markdown badge
    """
    return "[![vanity](https://img.shields.io/badge/vanity-{identifier}-f9f107.svg)](https://www.arxiv-vanity.com/papers/{identifer})"
