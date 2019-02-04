.. :changelog:

History
-------
0.5.0.tubular2 (2019-02-04)
++++++++++++++++++
Fix/cleanup nationalities and custom alias data files.

0.5.0.tubular1 (2019-01-30)
++++++++++++++++++
Instead of adding all top-level administrative divisions, add all administrative divisions with
population of at least 15000. This adds places like "Essex, England" and removes places like
"Portland, Jamaica".
Add support for a small number of custom aliases.
Add a few more common words to the blacklist, like "can" and "of".
Automatically blacklist 2-character strings if they contain lower-case, to prevent something like
"la liga" to match "LA" (Los Angeles).
Include country and state abbreviations when matching to improve disambiguation between places like
"Cambridge, MA" and "Cambridge, UK".
When calculating country mentions, use maximum population of matched entities to break ties
when multiple countries were mentioned the most often.
GeoText.index entries now map strings to (country_code, population) tuples instead of just
country_codes.
Fix errors in nationalities.txt

0.4.0.tubular1 (2019-01-14)
++++++++++++++++++
For cities with the same name, choose the most populous city when deciding which country to use
for country_mentions.
Support for alternate names of locations, like 'Istanbul'.
Support for top-level administrative divisions of countries, like 'California' and 'England'.
Added 'aggressive' param which supports case insensitive matching, matching of nationalities, and
a broader range of characer sets, including Korean, Chinese, Arabic, Thai, and Japanese.

0.3.0 (2017-12-03)
++++++++++++++++++
Support for Brazilian cities (credit to @joseluizcoe)

0.2.0 (2017-07-01)
++++++++++++++++++

* Python 3 support (credit to @freezer9)

0.1.0 (2014-01-11)
---------------------

* First release on PyPI.