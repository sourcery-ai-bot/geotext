# -*- coding: utf-8 -*-

from collections import namedtuple, Counter, OrderedDict
import re
import string
import os
import io

_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_data_path(path):
    return os.path.join(_ROOT, 'data', path)


def read_table(filename, keycols=(0,), valcol=1, sep='\t', comment='#', encoding='utf-8', skip=0):
    """Parse data files from the data directory

    Parameters
    ----------
    filename: string
        Full path to file

    keycols: list, default [0]
        A list of at least one int representing the columns to be used as keys
        for this dictionary

    valcol: int
        Index of the column containing the values to be saved into a dictionary

    sep : string, default '\t'
        Field delimiter.

    comment : str, default '#'
        Indicates remainder of line should not be parsed. If found at the beginning of a line,
        the line will be ignored altogether. This parameter must be a single character.

    encoding : string, default 'utf-8'
        Encoding to use for UTF when reading/writing (ex. `utf-8`)

    skip: int, default 0
        Number of lines to skip at the beginning of the file

    Returns
    -------
    A dictionary with the same length as the number of lines in `filename`
    """

    with io.open(filename, 'r', encoding=encoding) as f:
        # skip initial lines
        for _ in range(skip):
            next(f)

        # filter comment lines
        lines = (line for line in f if not line.startswith(comment))

        d = dict()
        for line in lines:
            columns = line.split(sep)
            value = columns[valcol].rstrip('\n')
            for key_index in keycols:
                key = normalize(columns[key_index].lower())
                d[key] = value
    return d


def build_index():
    """Load information from the data directory

    Returns
    -------
    A namedtuple with three fields: nationalities cities countries
    """

    nationalities = read_table(get_data_path('nationalities.txt'), sep=':')

    # parse http://download.geonames.org/export/dump/countryInfo.txt
    countries = read_table(
        get_data_path('countryInfo.txt'), keycols=[4], valcol=0, skip=1)

    # parse http://download.geonames.org/export/dump/cities15000.zip
    cities = read_table(get_data_path('cities15000.txt'), keycols=[1, 2], valcol=8)

    # load and apply city patches
    city_patches = read_table(get_data_path('citypatches.txt'))
    cities.update(city_patches)

    Index = namedtuple('Index', 'nationalities cities countries')
    return Index(nationalities, cities, countries)


def normalize(s):
    """Normalize punctuation and whitespace in location names and strings

    Returns
    -------
    String with some punctuation removed and some punctuation replace
    with spaces.
    """
    s = s.replace('.', '')
    s = re.sub(r'[,\-]', ' ', s)
    tokens = [t.strip(string.punctuation) for t in s.split()]
    return ' '.join(t for t in tokens if t)


class GeoText(object):

    """Extract cities and countries from a text

    Examples
    --------

    >>> places = GeoText("London is a great city")
    >>> places.cities
    "London"

    >>> GeoText('New York, Texas, and also China').country_mentions
    OrderedDict([(u'US', 2), (u'CN', 1)])

    """

    index = build_index()

    def __init__(self, text, country=None, aggressive=False):
        """
        Parameters
        ----------
        country: string
            Limit city matches to the country with this country code\

        aggressive: bool
            If True, be more liberal in finding candidate location names.  Ignore
            capitalization and some punctuation, and accept a wider range of
            characters.  This may be much slower for long text.
        """
        if aggressive:
            tokens = normalize(text).split()
            candidates = {
                ' '.join(tokens[i:i + length])
                for i in range(len(tokens))
                for length in range(1, 5)  # Assumes location names will be 4 words long at most
            }
        else:
            city_regex = r"[A-ZÀ-Ú]+[a-zà-ú]+[ \-]?(?:d[a-u].)?(?:[A-ZÀ-Ú]+[a-zà-ú]+)*"
            candidates = re.findall(city_regex, text)
            # Removing white spaces and normalizing punctuation from candidates
            candidates = [normalize(candidate) for candidate in candidates]
        self.countries = [each for each in candidates
                          if each.lower() in self.index.countries]
        self.cities = [each for each in candidates
                       if each.lower() in self.index.cities
                       # country names are not considered cities
                       and each.lower() not in self.index.countries]
        if country is not None:
            self.cities = [city for city in self.cities if self.index.cities[city.lower()] == country]

        self.nationalities = [each for each in candidates
                              if each.lower() in self.index.nationalities]

        # Calculate number of country mentions
        self.country_mentions = [self.index.countries[country.lower()]
                                 for country in self.countries]
        self.country_mentions.extend([self.index.cities[city.lower()]
                                      for city in self.cities])
        self.country_mentions.extend([self.index.nationalities[nationality.lower()]
                                      for nationality in self.nationalities])
        self.country_mentions = OrderedDict(
            Counter(self.country_mentions).most_common())

if __name__ == '__main__':
    print(GeoText('In a filing with the Hong Kong bourse, the Chinese cement producer said ...').countries)
