# -*- coding: utf-8 -*-

from collections import defaultdict, namedtuple, OrderedDict
from functools import partial
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

# Common words that are also nationalities / admin divisions / cities
BLACKLIST = {
    'asia', # a city in the Phillipines
    'bar',
    'bay',
    'can',
    'central',
    'eastern',
    'north',
    'northern',
    'of',
    'pole',
    'southern',
    'university',
    'western',
}


def read_table(
    filename, parse_keys=None, parse_value=None, sep='\t', comment='#', encoding='utf-8',
    skip=0, collect_set=False,
):
    """Parse data files from the data directory

    Parameters
    ----------
    filename: string
        Full path to file

    parse_keys: callable
        function that takes a single argument, a list representing a row of data, and returns
         a set of hashable objects to be used as keys in the dictionary being generated

    parse_values: callable
        function that takes a single argument, a list representing a row of data, and returns
         an object to be used as the value in the dictionary being generated

    sep : string, default '\t'
        Field delimiter.

    comment : str, default '#'
        Indicates remainder of line should not be parsed. If found at the beginning of a line,
        the line will be ignored altogether. This parameter must be a single character.

    encoding : string, default 'utf-8'
        Encoding to use for UTF when reading/writing (ex. `utf-8`)

    skip: int, default 0
        Number of lines to skip at the beginning of the file

    collect_set: bool
        if True, collect values for each row with the same key as a set instead of replacing
        previous values

    Returns
    -------
    A dictionary with the same length as the number of unique keys in filename, plus associated
    aliases.
    """

    with io.open(filename, 'r', encoding=encoding) as f:
        # skip initial lines
        for _ in range(skip):
            next(f)

        # filter comment lines
        lines = (line for line in f if line.strip() and not line.startswith(comment))

        d = defaultdict(set) if collect_set else dict()
        for line in lines:
            columns = line.rstrip('\n').split(sep)
            value = parse_value(columns)
            keys = parse_keys(columns)
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
    A namedtuple with five fields: nationalities cities countries admin_divisions meta
    """

    # get map of aliases keyed by geonameid
    aliases = read_table(
        get_data_path('alternateNamesFiltered.txt'), collect_set=True,
        parse_keys=lambda row: {row[1]},
        parse_value=lambda row: row[3],
    )

    # load custom aliases keyed by geonameid
    custom_aliases = read_table(
        get_data_path('alternateNamesCustom.txt'), collect_set=True,
        parse_keys=lambda row: {row[0]},
        parse_value=lambda row: row[1],
    )
    for geoname_id, alias_set in custom_aliases.items():
        aliases[geoname_id] |= alias_set

    def with_aliases(name_set, alias_key):
        if alias_key in aliases:
            name_set.update(aliases[alias_key])
        return name_set

    PlaceData = namedtuple('PlaceData', ['country', 'population'])
    def get_place_value(row, country_index=None, pop_index=None):
            population = 0 if pop_index is None else int(row[pop_index])
            return PlaceData(row[country_index], population)

    # parse http://download.geonames.org/export/dump/countryInfo.txt
    countries = read_table(
        get_data_path('countryInfo.txt'), skip=1,
        parse_keys=lambda row: with_aliases({row[4]}, row[16]),
        parse_value=partial(get_place_value, country_index=0, pop_index=7),
    )

    nationalities = read_table(
        get_data_path('nationalities.txt'), sep=':',
        parse_keys=lambda row: {row[0]},
        parse_value=partial(get_place_value, country_index=1),
    )
    for n in countries:
        nationalities.pop(n, None)

    def get_place_keys(row):
        """Parse geonames.org data for names of cities/administrative_divisions"""
        geo_id, official_name, name_alias = row[0:3]
        feature_type, country_code, _, admin1_code = row[7:11]
        names = with_aliases({official_name, name_alias}, geo_id)
        for name in list(names):
            # Add names with country/state abbreviatiosn to better disambiguate cases
            # like "Cambridge, MA" and "Cambridge, UK"
            names.add(' '.join((name, country_code)))
            if country_code == 'GB':
                names.add(' '.join((name, 'UK')))
            if admin1_code and not feature_type.startswith('ADM1'):
                names.add(' '.join((name, admin1_code)))
        return names

    # parse http://download.geonames.org/export/dump/cities15000.zip
    cities = read_table(
        get_data_path('cities15000.txt'),
        parse_keys=get_place_keys,
        parse_value=partial(get_place_value, country_index=8, pop_index=14),
    )

    # add country divisions like US States and Japanese Prefectures
    admin_divisions = read_table(
        get_data_path('adminDivisions15000.txt'),
        parse_keys=get_place_keys,
        parse_value=partial(get_place_value, country_index=8, pop_index=14),
    )

    meta = defaultdict(set)
    for match_type, index in [
        (CITIES, cities),
        (ADMIN_DIVISIONS, admin_divisions),
        (NATIONALITIES, nationalities),
        (COUNTRIES, countries),
    ]:
        for name in index:
            if name not in BLACKLIST:
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
        parsed = self.parse_aggressive(text) if aggressive else self.parse(text)
        self.countries = parsed[COUNTRIES]
        self.admin_divisions = parsed[ADMIN_DIVISIONS]
        self.cities = parsed[CITIES]
        self.nationalities = parsed[NATIONALITIES]

        if country is not None:
            self.cities = [
                city for city in self.cities
                if self.index.cities[city.lower()].country == country
            ]
            self.admin_divisions = [
                division for division in self.admin_divisions
                if self.index.cities[division.lower()] == country
            ]
            self.nationalities = [
                nationality for nationality in self.nationalities
                if self.index.nationalities[nationality.lower()] == country
            ]

        # Tabulate the number of times each country was mentioned
        # Order countries by number of different mentions and break ties using
        # the maximum population of locations matched
        max_population = defaultdict(int)
        mentions = defaultdict(int)
        seen = set()
        for match_type in MATCH_TYPES:
            index = getattr(self.index, match_type)
            new_matches = []
            for match_string in parsed[match_type]:
                country, population = index[match_string.lower()]
                max_population[country] = max(max_population[country], population)
                if (country, match_string) not in seen:
                    # Don't count the same string multiple times for the same country
                    # This could happen if a string is both a city and an admin_division in the
                    # same country.
                    mentions[country] += 1
                    new_matches.append((country, match_string))
            # Update "seen" only after each type has been completely processed so that
            # "China China China" will correctly count as "{'CN': 3}" country_mentions.
            seen.update(new_matches)

        self.country_mentions = OrderedDict(
            sorted(
                mentions.items(),
                key=lambda x: (x[1], max_population[x[0]]),
                reverse=True
            )
        )

    @classmethod
    def parse_aggressive(cls, text):
        tokens = normalize(text).split()
        matches = {match_type: [] for match_type in MATCH_TYPES}

        # Track match length so we don't include substrings of previous matches
        # "New York City" should not match "New York" or "York"
        prev_match_len = 0
        for i in range(len(tokens)):
            prev_match_len = max(prev_match_len - 1, 0)
            # Assumes location names will be 4 words long at most
            for length in range(min(4, len(tokens) - i), prev_match_len, -1):
                candidate = ' '.join(tokens[i:i + length])
                if len(candidate) < 3 and any(c.islower() for c in candidate):
                    # skip 2-char strings like 'la', but not 'LA' or '中国'
                    continue
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
