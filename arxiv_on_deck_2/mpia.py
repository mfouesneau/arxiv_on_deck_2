"""
MPIA related functions.

This module handles the list of MPIA authors to monitor.
Eventually Scientists should provide their publication names.
"""

from typing import Sequence
from bs4 import BeautifulSoup
import requests


def parse_mpia_staff_list() -> Sequence[str]:
    """ Parse the multi-page table from the MPIA website and returns the name column
    :returns: list of names (full names)
    """
    mitarbeiter_url = 'https://www.mpia.de/institut/mitarbeiter?letter=Alle&seite={pagenum}'
    data = []
    for pagenum in range(1, 100):
        # print(f'parsing page {pagenum}')
        response = requests.get(mitarbeiter_url.format(pagenum=pagenum))
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        lst = soup.find_all('span', attrs={'class': 'employee_name'})
        if not lst:
            break
        data.extend([k.text for k in lst])
    return data


def get_initials(name: str) -> str:
    """ Get the short name, e.g., A.-B. FamName
    :param name: full name
    :returns: initials
    """
    initials = []
    split = name.split()
    for token in split[:-1]:
        if '-' in token:
            current = '-'.join([k[0] + '.' for k in token.split('-')])
        else:
            current = token[0] + '.'
        initials.append(current)
    initials.append(split[-1])
    return ' '.join(initials)

def get_special_corrections(initials_name:str) -> str:
    """ Handle non-generic cases of initials
    :param initials_name: name with initials
    :returns: name with corrected initials
    """
    # non-generic cases
    collected = {
    'S. R. Khoshbakht': 'S. Rezaei Kh.',
    'E. B. Torres': 'E. Bañados',
    }

    try:
        return collected[initials_name]
    except KeyError:
        return initials_name


def filter_non_scientists(name: str) -> bool:
    """ Loose filter on expected authorships

    removing IT, administration, technical staff
    :param name: name
    :returns: False if name is not a scientist
    """
    remove_list = ['Wolf', 'Licht', 'Binroth', 'Witzel', 'Jordan',
                   'Zähringer', 'Scheerer', 'Hoffmann', 'Düe',
                   'Hellmich', 'Enkler-Scharpegge', 'Witte-Nguy',
                   'Dehen', 'Beckmann'
                  ]

    for k in remove_list:
        if k in name:
            return False
    return True


def family_name_from_initials(initials: str) -> str:
    """ Get family name only
    :param initials: name with initials
    :returns: family name
    """
    pattern = '. '.join(initials[:-1].split('. ')[:-1]) + '.'
    return initials.replace(pattern, '').strip()


def consider_variations(name: str) -> str:
    """ Consider a name with the usual character replacements
    :param name: name
    :returns: name with replacements
    """
    # German umlaut, French accents
    new_name = name.replace("ö", "oe")\
                   .replace("ü", "ue")\
                   .replace("ä", "ae")\
                   .replace("ø", "oe")\
                   .replace("ß", "ss")\
                   .replace("é", "e")\
                   .replace("è", "e")\
                   .replace("ê", "e")\
                   .replace("î", "i")\
                   .replace("û", "u")\
                   .replace("ç", "c")
    if new_name != name:
        return new_name


def get_mpia_mitarbeiter_list() -> Sequence[str]:
    """ Get the main filtered list
    :returns: list of names (family name, full names, initials)
    """
    data = parse_mpia_staff_list()
    filtered_data = list(filter(filter_non_scientists, data))

    name_variations = filter(lambda x: x is not None,
                             [consider_variations(name) for name in filtered_data])
    mitarbeiter_list = sorted(filtered_data + list(name_variations))

    lst = [(get_special_corrections(get_initials(name)), name) for name in mitarbeiter_list]
    lst = [(family_name_from_initials(k[0]), k[0], k[1]) for k in lst]
    lst = sorted(lst, key=lambda x: x[0])
    return lst


def affiliation_verifications(content: str,
                              word_list: Sequence[str] = None,
                              verbose: bool = False) -> bool:
    """ Check if specific keywords are present
        to make sure at least one author is MPIA.
        Test is case insensitive but all words must appear.

    :param content: text to check
    :param word_list: list of words required for verification
    :param verbose: print information
    :returns: True if all words are present
    """
    if word_list is None:
        word_list = ['Heidelberg', 'Max', 'Planck', '69117']
    check = True
    for word in word_list:
        if (word in content) or (word.lower() in content.lower()):
            check = check and True
        else:
            if verbose:
                return ("'{0:s}' keyword not found.".format(word))
            return False
    return check
