from glob import glob
from itertools import chain
from pybtex.database import parse_file
from pybtex.database import BibliographyData, Entry
from typing import Union, Sequence
import os
import re
import warnings
from .latex import LatexDocument

def clean_special_characters(source: str) -> str:
    """ Replace latex macros of special characters (accents etc) for their unicode alternatives

    :param source: bibitem raw string definition
    :return: transformed bibitem string definition
    """
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
    return source


def parse_bbl(fname: str) -> BibliographyData:
    """ Parse bibliographic information from bbl file (compiled bibliography)

    :param fname: filename to read the data from
    :return: biblio data object
    """

    def extract_bibitem_info(item_str: str) -> dict:
        """Get groups of info from bibitem definition

        Thanks to https://regex101.com/
        """
        regex_href = r"""
        \\bibitem(\[[^\[\]]*?\]){(?P<bibkey>[a-zA-Z0-9\-\+\.\S]+)}(?P<authors>|([\D]*?))(?P<year>[12][0-9]{3}).*?href(.*?{(?P<url>http[\S]*)})(?P<rest>.*)
        """
        regex_nohref = r"""
        \\bibitem(\[[^\[\]]*?\]){(?P<bibkey>[a-zA-Z0-9\-\+\.\S]+)}(?P<authors>|([\D]*?))(?P<year>[12][0-9]{3})(?P<rest>.*)
        """

        # You can manually specify the number of replacements by changing the 4th argument
        regex = regex_href if r'\href' in item_str else regex_nohref

        # replace special characters
        item_str = clean_special_characters(item_str)

        matches = re.search(regex, item_str.replace('\n', ' '),
                            re.DOTALL | re.IGNORECASE | re.VERBOSE | re.MULTILINE)

        try:
            info = matches.groupdict()
        except AttributeError as e:
            raise RuntimeError(f"Error processing bibitem\n item = {item_str}\n regex = {regex}")
        info.setdefault('title', "")
        info.setdefault('url', "")
        return info

    def find_bibitem(sample: str) -> Sequence[str]:
        """ Find bibitem definitions in a string"""
        entries = re.findall(r'(\\bibitem)((.(?!bibitem))*)',
                             sample, re.DOTALL | re.IGNORECASE | re.VERBOSE | re.MULTILINE)
        entries = [''.join(entry).replace('\n', '').strip() for entry in entries]
        return entries

    def clean_author(authors):
        """ Put things in the right format for bibtex """
        regex = r"(?P<last>{[\w{}\~\-\\]+})[,\s]+?(?P<first>[\w{}\~\-\\\.\s]+),*"
        return ['{0:s}, {1:s}'.format(*it)
                for it in re.findall(regex, authors.strip())]

    def get_bibtex_code(rk: dict):
        tpl = """
@article{{{bibkey:s},
  title = "{title:s}",
  author = {{{authors:s}}},
  url = "{url:s}",
  year = "{year:s}"
}}
"""
        rk['authors'] = ' and '.join(clean_author(rk['authors']))
        return tpl.format(**rk)

    # Read file
    with open(fname, 'r') as fin:
        content = fin.read()

    # identify entries
    entries = find_bibitem(content)
    n_entries = len(entries)
    print(f"Found {n_entries:,d} bibliographic references in {fname:s}.")

    # extract individual fields per entry
    r = []
    for it in entries:
        try:
            r.append(extract_bibitem_info(it))
        except RuntimeError as e:
            warnings.warn(str(e))

    # create the bibtex text
    bibtex = ''.join(get_bibtex_code(rk) for rk in r)
    return BibliographyData.from_string(bibtex, 'bibtex')


def merge_BibliographyData(dbs: Sequence[BibliographyData]) -> BibliographyData:
    """ Merge BibliographyData objects

    :param dbs: Sequence of bibliographic data objects
    :return: single bibliographic data with all entries from dbs
    """
    b = BibliographyData()
    b = BibliographyData()
    for bdata in dbs:
        for key, entry in bdata.entries.items():
            b.add_entry(key, entry)
    return b


class LatexBib:
    """ A small interface to pybtex to handle bibliography entries """
    def __init__(self, bibdata: BibliographyData):
        """ Constructor

        :param bibdata: the bibliography object class from pybtex
        """
        self.bibdata = bibdata

    def _key_or_entry(self, key_or_entry: Union[str, Entry]) -> Entry:
        """ A check on argument type. Returns a corresponding entry

        :param key_or_entry: either key string or the bib entry
        :return: the corresponding bib entry
        """
        if isinstance(key_or_entry, Entry):
            return key_or_entry
        else:
            return self.bibdata.entries[key_or_entry]

    def get_short_authors(self, key: Union[str, Entry], max_authors: int = 3) -> str:
        """ Returns the astro style author list (e.g., bob et al.)

        :param key: key to extract from
        :param max_authors: the number of authors to allow before "et. al" abbrv.
        :return: short string of authors (e.g., lada and lada, a, b and c, bob et al)
        """
        entry = self._key_or_entry(key)

        # short name
        get_name_only = lambda author: ' '.join(author.last_names).replace('{', '').replace('}', '')
        lst = [get_name_only(k) for _, k in zip(range(4), entry.persons['author'])]

        if len(lst) > max_authors:
            authors = ', '.join((lst[0], 'et. al'))
        else:
            authors = ', '.join(k for k in lst[:-1]) + ' and ' + lst[-1]
        return authors

    def get_year(self, key: Union[str, Entry]) -> str:
        """ return refrence's publication year

        :param key: key to extract from
        :return: the publication year (entry.field['year'])
        """
        entry = self._key_or_entry(key)

        return entry.fields['year']

    def get_url(self, key: Union[str, Entry]) -> str:
        """ Extract if possible the URL of the bib entry
        It will attempt to use the url, or adsurl, or doi entries in that order.

        :param key: key to extract from
        :return: string of the url (or empty string)
        """
        entry = self._key_or_entry(key)
        # get url
        if 'url' in entry.fields:
            url = entry.fields['url']
        elif 'adsurl' in entry.fields:
            url = entry.fields['adsurl']
        elif 'doi' in entry.fields:
            url = 'https://doi.org/' + entry.fields['doi']
        else:
            url = ''
        return url

    def get_citation_text(self, key: Union[str, Entry],
                          kind: str = 'cite',
                          max_authors: int = 3) -> str:
        """ Return formatted text

        examples:
        * `kind="citet"` -> author1, et al. (2023)
        * `kind="cite"` -> author1 and author2 2023

        :param key: key to extract from
        :param kind: the kind of latex citation (expecting cite, citealt, citet, citep)
        :param max_authors: the number of authors to allow before "et. al" abbrv.
        :return: the formatted citation text
        """

        entry = self._key_or_entry(key)

        authors = self.get_short_authors(entry, max_authors=max_authors)
        year = self.get_year(entry)

        if kind in ('citep', ):
            citation_text = f"{authors} {year}"
        elif kind in ('citealt', ):
            citation_text = f"{authors} {year}"
        else:
            citation_text = f"{authors} ({year})"
        return citation_text

    def get_citation_md(self, key: Union[str, Entry],
                        kind: str = 'cite',
                        max_authors: int = 3) -> str:
        """ Return formatted markdown string

        examples:
        * `kind="citet"` -> [author1, et al. (2023)](url)
        * `kind="cite"` -> [author1 and author2 2023](url)

        :param key: key to extract from
        :param kind: the kind of latex citation (expecting cite, citealt, citet, citep)
        :param max_authors: the number of authors to allow before "et. al" abbrv.
        :return: the formatted citation text
        """
        entry = self._key_or_entry(key)

        citation_text = self.get_citation_text(entry, kind, max_authors)
        url = self.get_url(entry)
        citation_md = f"[{citation_text}]({url})"
        return citation_md

    @classmethod
    def from_doc(cls, doc: LatexDocument):
        """Create from a LatexDocument object

        First check if there is any `.bbl` file with the document,
        if not attempts to read the `.bib` file instead.

        :param doc: the document to link with
        :return: LatexBib object

        TODO: extract bibitems entries from main doc if any
        """
        bbl_files = glob(os.path.join(doc.folder, '*.bbl'))
        if bbl_files:
            bib_data = [parse_bbl(fname) for fname in bbl_files]
        else:
            bibfiles = doc.content.find_all('bibliography')[0].text
            bibfiles = list(*chain([glob(os.path.join(doc.folder, bk + '*')) for bk in bibfiles]))
            bib_data = []
            for bibfile in bibfiles:
                with open(str(bibfile)) as bibtex_file:
                    bib_database = parse_file(bibtex_file)
                bib_data.append(bib_database)
        bib_data = merge_BibliographyData(bib_data)

        return cls(bib_data)


def replace_citations(full_md: str, bibdata: LatexBib, kind='all'):
    """ Parse and replace \citex calls remaining in the Markdown text

    :param full_md: Markdown document
    :param bibdata: the bibliographic data
    :param kind: which of \citex macros (all, citet, citep, citealt)
    :return: updated content
    """
    allowed = ('all', 'citet', 'citep', 'citealt', 'cite')

    if kind not in allowed:
        raise RuntimeError(f"expected kind in {allowed}. Got {kind}.")

    if kind == 'all':
        new_text = full_md[:]
        for kind in ('citep', 'citet', 'cite', 'citealt'):
            new_text = replace_citations(new_text, bibdata, kind=kind)
        return new_text

    new_text = ""
    last_pos = 0

    r = re.finditer(r"(\\" + kind + r"{)(.*?)\}", full_md)
    for rk in r:
        keys = rk.groups()[1].split(',')
        values = [bibdata.get_citation_md(key.strip(), kind=kind) for key in keys]
        mdtext = ' (' + ', '.join(values) + ') '
        new_text = ''.join((new_text,
                           full_md[last_pos: rk.start()],
                           mdtext))
        last_pos = rk.end()
    new_text = ''.join((new_text,
                        full_md[last_pos:]))
    return new_text
