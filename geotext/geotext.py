# -*- coding: utf-8 -*-

from collections import defaultdict, namedtuple, Counter, OrderedDict
import re
import string
import os
import io

_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_data_path(path):
    return os.path.join(_ROOT, 'data', path)


COUNTRIES = 'countries'
ADMIN_DIVISIONS = 'admin_divisions'
CITIES = 'cities'
NATIONALITIES = 'nationalities'
MATCH_TYPES = {COUNTRIES, ADMIN_DIVISIONS, CITIES, NATIONALITIES}

# Common words that are also nationalities / admin divisions
BLACKLIST = {
    'pole',
    'north',
    'northern',
    'western',
    'central',
    'southern',
    'eastern',
}


def read_table(
    filename, keycols=(0,), valcol=1, sep='\t', comment='#', encoding='utf-8', skip=0,
    alias_keycol=None, aliases=None, collect_set=False
):
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

    alias_keycol: int
        if not None, this column will be used to look up aliases for this column in the
        provided `aliases` dict.  For each row, aliases are additional keys that will map
        the row's value.

    aliases: dict
        dictionary mapping strings to sets of strings to be used as additional keys for each row

    collect_set: bool
        if True, collect values for each row with the same key as a set instead of replacing
        previous values

    Returns
    -------
    A dictionary with the same length as the number of unique keys in filename, plus associated
    aliases.  Values may be a strings or sets of strings, depending on the `collect_set` param.
    """

    with io.open(filename, 'r', encoding=encoding) as f:
        # skip initial lines
        for _ in range(skip):
            next(f)

        # filter comment lines
        lines = (line for line in f if not line.startswith(comment))

        d = defaultdict(set) if collect_set else dict()
        for line in lines:
            columns = line.split(sep)
            value = columns[valcol].rstrip('\n')
            keys = {columns[key_index] for key_index in keycols}
            if alias_keycol is not None:
                alias_key = columns[alias_keycol]
                keys |= aliases[alias_key]
            for key in keys:
                key = normalize(key.lower())
                if collect_set:
                    d[key].add(value)
                else:
                    d[key] = value
    return d


def build_index():
    """Load information from the data directory

    Returns
    -------
    A namedtuple with three fields: nationalities cities countries
    """

    # get map of aliases keyed by geonameid
    aliases = read_table(
        get_data_path('alternateNamesFiltered.txt'), keycols=[1], valcol=3, collect_set=True
    )


    # parse http://download.geonames.org/export/dump/countryInfo.txt
    countries = read_table(
        get_data_path('countryInfo.txt'), keycols=[4], valcol=0, skip=1,
        alias_keycol=16, aliases=aliases
    )

    # parse http://download.geonames.org/export/dump/cities15000.zip
    cities = read_table(
        get_data_path('cities15000.txt'), keycols=[1, 2], valcol=8,
        alias_keycol=0, aliases=aliases
    )
    # load and apply city patches
    city_patches = read_table(get_data_path('citypatches.txt'))
    cities.update(city_patches)
    # Always choose countries over cities
    cities = {city: country for city, country in cities.items() if city not in countries}

    nationalities = read_table(get_data_path('nationalities.txt'), sep=':')
    nationalities = {n: country for n, country in nationalities.items() if n not in countries}

    # add top-level country divisions like US States and Japanese Prefectures
    admin_divisions = read_table(
        get_data_path('admin_divisions1.txt'), keycols=[1, 2], valcol=8,
        alias_keycol=0, aliases=aliases
    )

    meta = defaultdict(set)
    for match_type, index in [
        (CITIES, cities),
        (ADMIN_DIVISIONS, admin_divisions),
        (NATIONALITIES, nationalities),
        (COUNTRIES, countries),
    ]:
        for name in index:
            if name in BLACKLIST:
                continue
            meta[name].add(match_type)

    Index = namedtuple('Index', [NATIONALITIES, CITIES, COUNTRIES, ADMIN_DIVISIONS, 'meta'])
    return Index(nationalities, cities, countries, admin_divisions, meta)


def normalize(s):
    """Normalize punctuation and whitespace in location names and strings

    Returns
    -------
    String with some punctuation removed and some punctuation replace
    with spaces.
    """
    s = s.replace('.', '')
    s = re.sub(r'[|\\/,\-]', ' ', s)
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
            parsed = self.parse_aggressive(text)
        else:
            parsed = self.parse(text)
        self.countries = parsed[COUNTRIES]
        self.admin_divisions = parsed[ADMIN_DIVISIONS]
        self.cities = parsed[CITIES]
        self.nationalities = parsed[NATIONALITIES]

        if country is not None:
            self.cities = [
                city for city in self.cities
                if self.index.cities[city.lower()] == country
            ]
            self.admin_divisions = [
                division for division in self.admin_divisions
                if self.index.cities[division.lower()] == country
            ]
            self.nationalities = [
                nationality for nationality in self.nationalities
                if self.index.nationalities[nationality.lower()] == country
            ]

        # Calculate number of country mentions
        self.country_mentions = [self.index.countries[country.lower()]
                                 for country in self.countries]
        self.country_mentions.extend([self.index.nationalities[nationality.lower()]
                                      for nationality in self.nationalities])
        self.country_mentions.extend([self.index.cities[city.lower()]
                                      for city in self.cities
                                      if city not in self.admin_divisions])
        self.country_mentions.extend([self.index.admin_divisions[division.lower()]
                                      for division in self.admin_divisions
                                      if division not in self.nationalities])
        self.country_mentions = OrderedDict(
            Counter(self.country_mentions).most_common())

    @classmethod
    def parse_aggressive(cls, text):
        tokens = normalize(text).split()
        matches = {match_type: [] for match_type in MATCH_TYPES}

        prev_match_len = 0  # Track match length so we don't include substrings of previous matches
        for i in range(len(tokens)):
            prev_match_len = max(prev_match_len - 1, 0)
            # Assumes location names will be 4 words long at most
            for length in range(min(4, len(tokens) - i), prev_match_len, -1):
                candidate = ' '.join(tokens[i:i + length])
                match_types = cls.index.meta.get(candidate.lower())
                if not match_types:
                    continue
                for match_type in match_types:
                    matches[match_type].append(candidate)
                prev_match_len = length
                break
        return matches

    @classmethod
    def parse(cls, text):
        matches = {match_type: [] for match_type in MATCH_TYPES}
        city_regex = r"[A-ZÀ-Ú]+[a-zà-ú]+[ \-]?(?:d[a-u].)?(?:[A-ZÀ-Ú]+[a-zà-ú]+)*"
        for candidate in re.findall(city_regex, text):
            candidate = candidate.strip()
            match_types = cls.index.meta.get(normalize(candidate).lower())
            if not match_types:
                continue
            for match_type in match_types:
                matches[match_type].append(candidate)
        # Nationalities, like 'Spanish', often don't refer to locations, so don't return
        # these results unless we are using aggressive parsing
        matches[NATIONALITIES] = []
        return matches


if __name__ == '__main__':
    print(GeoText('In a filing with the Hong Kong bourse, the Chinese cement producer said ...').countries)
