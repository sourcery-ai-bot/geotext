#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_geotext
----------------------------------

Tests for `geotext` module.
"""

import unittest
import geotext


class TestGeotext(unittest.TestCase):
    def setUp(self):
        pass

    def test_cities(self):

        text = """São Paulo é a capital do estado de São Paulo. As cidades de Barueri
                  e Carapicuíba fazem parte da Grade São Paulo. O Rio de Janeiro
                  continua lindo. No carnaval eu vou para Salvador. No reveillon eu
                  quero ir para Santos."""
        result = geotext.GeoText(text).cities
        expected = [
            'São Paulo', 'São Paulo', 'Barueri', 'Carapicuíba', 'Rio de Janeiro', 'Salvador', 'Santos'
        ]
        self.assertEqual(result, expected)

        brazillians_northeast_capitals = """As capitais do nordeste brasileiro são:
                                            Salvador na Bahia,
                                            Recife em Pernambuco,
                                            Natal fica no Rio Grande do Norte,
                                            João Pessoa fica na Paraíba,
                                            Fortaleza fica no Ceará,
                                            Teresina no Piauí,
                                            Aracaju em Sergipe,
                                            Maceió em Alagoas e
                                            São Luís no Maranhão."""
        result = geotext.GeoText(brazillians_northeast_capitals).cities
        # PS: 'Rio Grande' is not a northeast city, but is a brazilian city
        expected = [
            'Salvador', 'Recife', 'Natal', 'Rio Grande', 'João Pessoa', 'Fortaleza', 'Teresina', 'Aracaju', 'Maceió', 'São Luís'
        ]
        self.assertEqual(result, expected)


        brazillians_north_capitals = """As capitais dos estados do norte brasileiro são:
                                        Manaus no Amazonas,
                                        Palmas em Tocantins,
                                        Belém no Pará,
                                        Acre no Rio Branco."""
        result = geotext.GeoText(brazillians_north_capitals).cities
        expected = [
            'Manaus', 'Palmas', 'Belém', 'Rio Branco'
        ]
        self.assertEqual(result, expected)

        brazillians_southeast_capitals = """As capitais da região sudeste do Brasil são:
                                            Rio de Janeiro no Rio de Janeiro,
                                            São Paulo em São Paulo,
                                            Belo Horizonte em Minas Gerais,
                                            Vitória no Espírito Santo"""
        result = geotext.GeoText(brazillians_southeast_capitals).cities
        # 'Rio de Janeiro' and 'Sao Paulo' city and state name are the same, so appears 2 times, it's ok!
        expected = [
            'Rio de Janeiro', 'Rio de Janeiro', 'São Paulo', 'São Paulo', 'Belo Horizonte', 'Vitória'
        ]
        self.assertEqual(result, expected)

        brazillians_central_capitals = """As capitais da região centro-oeste do Brasil são:
                                          Goiânia em Goiás,
                                          Brasília no Distrito Federal,
                                          Campo Grande no Mato Grosso do Sul,
                                          Cuiabá no Mato Grosso."""
        result = geotext.GeoText(brazillians_central_capitals).cities
        expected = [
            'Goiânia', 'Goiás', 'Brasília', 'Campo Grande', 'Cuiabá'
        ]
        self.assertEqual(result, expected)

        brazillians_south_capitals = """As capitais da região sul são:
                                        Porto Alegre no Rio Grande do Sul,
                                        Santa Catarina,
                                        Curitiba no Paraná"""
        result = geotext.GeoText(brazillians_south_capitals).cities
        # PS: 'Rio Grande' is not a south city, but is a brazilian city
        expected = [
            'Porto Alegre', 'Rio Grande', 'Santa Catarina', 'Curitiba', 'Paraná'
        ]
        self.assertEqual(result, expected)

        result = geotext.GeoText('Rio de Janeiro y Havana', 'BR').cities
        expected = [
            'Rio de Janeiro'
        ]
        self.assertEqual(result, expected)

        result = geotext.GeoText('Floripa! Istanbul! Bukarest!').cities
        # Istanbul is the ASCII name for İstanbul, Bucureşti is Romanian for Bucharest
        expected = [
            'Floripa', 'Istanbul', 'Bukarest',
        ]
        self.assertEqual(result, expected)

    def test_nationalities(self):

        text = 'Japanese people like anime. French people often drink wine. Chinese people enjoy fireworks.'
        result = geotext.GeoText(text, aggressive=True).nationalities
        expected = ['Japanese', 'French', 'Chinese']
        self.assertEqual(result, expected)

    def test_countries(self):

        text = """That was fertile ground for the emergence of various forms of
                  totalitarian governments such as Japan, Italy,
                  and Germany, as well as other countries"""
        result = geotext.GeoText(text).countries
        expected = ['Japan', 'Italy', 'Germany']
        self.assertEqual(result, expected)

    def test_country_mentions(self):

        text = 'I would like to visit Lima, Dublin and Moscow (Russia).'
        result = geotext.GeoText(text).country_mentions
        expected = {'PE': 1, 'IE': 1, 'RU': 2}
        self.assertEqual(result, expected)

    def test_aggressive(self):

        text = 'Washington, D.C., paris? INDIA, 日本, and București!'
        result = geotext.GeoText(text, aggressive=True)
        expected_countries = {'INDIA', '日本'}
        expected_cities = {'paris', 'Washington DC', 'București'}
        self.assertEqual(set(result.countries), expected_countries)
        self.assertEqual(set(result.cities), expected_cities)

    def test_admin_divisions(self):

        text = 'The sun is nice in Florida and the snow is nice in Hokkaido'
        result = geotext.GeoText(text).admin_divisions
        expected = ['Florida', 'Hokkaido']
        self.assertEqual(result, expected)

    def test_match_length(self):

        text = 'These should only be cities: San Francisco, New York City'
        expected_cities = ['San Francisco', 'New York City']  # should not match "San" or "York"
        expected_admin_divisions = []  # should not match the U.S. state, "New York"

        result = geotext.GeoText(text, aggressive=True)
        self.assertEqual(result.cities, expected_cities)
        self.assertEqual(result.admin_divisions, expected_admin_divisions)

        text = 'I am not sure what city you mean by San Francisco Beltrao'
        result = geotext.GeoText(text, aggressive=True).cities
        expected = ['San Francisco', 'Francisco Beltrao']  # should not match "San" or "York"
        self.assertEqual(result, expected)

        text = 'I am not sure what city you mean by La Isla Vista'
        result = geotext.GeoText(text, aggressive=True).cities
        expected = ['La Isla', 'Isla Vista']  # should not match "Vista"
        self.assertEqual(result, expected)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
