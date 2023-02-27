from glob import glob
from itertools import chain
from pybtex.database import parse_file
from pybtex.database import BibliographyData, Entry
from typing import Union
import os
from .latex import LatexDocument

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
        
        :param doc: the document to link with
        :return: LatexBib object
        """
    
        bibfiles = doc.content.find_all('bibliography')[0].text
        bibfiles = list(*chain([glob(os.path.join(doc.folder, bk + '*')) for bk in bibfiles]))

        bib_data = []
        for bibfile in bibfiles:
            with open(str(bibfile)) as bibtex_file:
                bib_database = parse_file(bibtex_file)
            bib_data.append(bib_database)
    
        b0 = bib_data[0]
        for bdata in bib_data[1:]:
            b0.add_entries(bdata.entries)

        return cls(b0)
    

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
        print(str(rk))
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
