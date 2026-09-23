"""Unit tests for financial extraction and anti-fabrication scale normalization."""

import unittest
from signalpost.extraction.financials import (
    detect_scale_factor,
    normalize_financial_statement,
    parse_norwegian_number,
)


class FinancialNormalizationTests(unittest.TestCase):
    def test_missing_values_never_become_zero(self):
        self.assertIsNone(parse_norwegian_number(None))
        self.assertIsNone(parse_norwegian_number(""))
        self.assertIsNone(parse_norwegian_number("-"))
        self.assertIsNone(parse_norwegian_number("N/A"))

    def test_zero_is_preserved_when_explicitly_zero(self):
        self.assertEqual(parse_norwegian_number(0), 0.0)
        self.assertEqual(parse_norwegian_number("0"), 0.0)
        self.assertEqual(parse_norwegian_number("0,0"), 0.0)

    def test_norwegian_thousands_formatting(self):
        # 1 250 500 NOK formatted with spaces
        val = parse_norwegian_number("1 250 500")
        self.assertEqual(val, 1250500.0)

    def test_negative_values_in_parentheses(self):
        # Norwegian accounting reports negative profits in parentheses: (25 400) -> -25400
        val = parse_norwegian_number("(25 400)")
        self.assertEqual(val, -25400.0)

    def test_scale_multiplier_thousands(self):
        # Table reports figures in thousands (NOK 1 000)
        scale = detect_scale_factor("Resultatregnskap (tall i hele tusen NOK)")
        self.assertEqual(scale, 1000.0)

        # 24 300 thousand NOK = 24 300 000 NOK
        val = parse_norwegian_number("24 300", scale_multiplier=scale)
        self.assertEqual(val, 24_300_000.0)

    def test_scale_multiplier_millions(self):
        scale = detect_scale_factor("Beløp i MNOK")
        self.assertEqual(scale, 1_000_000.0)

        val = parse_norwegian_number("12,5", scale_multiplier=scale)
        self.assertEqual(val, 12_500_000.0)

    def test_statement_normalization_pipeline(self):
        raw_statement = {
            "id": 998877,
            "regnskapstype": "SELSKAP",
            "regnskapsperiode": "2025-01-01 - 2025-12-31",
            "valuta": "NOK",
            "resultatregnskapResultat": {
                "driftsresultat": {
                    "driftsinntekter": {
                        "sumDriftsinntekter": 54200000,
                    },
                    "driftsresultat": 8300000,
                },
                "ordinaertResultatFoerSkattekostnad": 7900000,
                "aarsresultat": 6162000,
            },
            "eiendeler": {
                "sumEiendeler": 42000000,
            },
            "egenkapitalGjeld": {
                "egenkapital": {
                    "sumEgenkapital": 19500000,
                },
                "gjeldOversikt": {
                    "sumGjeld": 22500000,
                },
            },
        }

        normalized = normalize_financial_statement(raw_statement)
        self.assertEqual(normalized["revenue"], 54_200_000.0)
        self.assertEqual(normalized["operating_result"], 8_300_000.0)
        self.assertEqual(normalized["profit_before_tax"], 7_900_000.0)
        self.assertEqual(normalized["annual_result"], 6_162_000.0)
        self.assertEqual(normalized["assets"], 42_000_000.0)
        self.assertEqual(normalized["equity"], 19_500_000.0)
        self.assertEqual(normalized["debt"], 22_500_000.0)
