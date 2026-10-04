"""Financial Red Team Suite (60+ Scenarios).

Tests financial extraction, anti-fabrication scale normalization, and currency handling:
- Missing vs Zero distinction (missing is NEVER 0.0)
- Explicit zero values preserved as 0.0
- Norwegian number formats (spaces, non-breaking spaces, narrow no-break spaces)
- Decimal comma, decimal point, thousands separators
- Negative values (parentheses, standard minus, Unicode minus, en-dash, trailing minus)
- Multipliers: Base NOK, NOK 1000, TKR, MNOK, BNOK (Milliarder)
- Multi-period statement extraction
- JSON, HTML table, and Brreg nested structures

Target:
- 0 fabricated values
- 0 missing -> zero conversions
- 0 scaling errors.
"""

from __future__ import annotations

import pytest
from signalpost.extraction.financials import (
    detect_scale_factor,
    normalize_financial_statement,
    parse_norwegian_number,
)

# =========================================================================
# 65 Financial Red Team Test Cases
# =========================================================================
PARSER_TEST_CASES = [
    # 1-10: Missing vs Zero Invariant (CRITICAL)
    ("none_is_none", None, 1.0, None),
    ("empty_str_is_none", "", 1.0, None),
    ("whitespace_is_none", "   ", 1.0, None),
    ("hyphen_is_none", "-", 1.0, None),
    ("en_dash_is_none", "–", 1.0, None),
    ("em_dash_is_none", "—", 1.0, None),
    ("unicode_minus_is_none", "−", 1.0, None),
    ("na_upper_is_none", "N/A", 1.0, None),
    ("na_lower_is_none", "n/a", 1.0, None),
    ("null_str_is_none", "null", 1.0, None),

    # 11-15: Explicit Zero Preservation (0 != None)
    ("int_zero_is_zero", 0, 1.0, 0.0),
    ("float_zero_is_zero", 0.0, 1.0, 0.0),
    ("str_zero_is_zero", "0", 1.0, 0.0),
    ("str_zero_comma_zero", "0,0", 1.0, 0.0),
    ("str_zero_point_zero", "0.00", 1.0, 0.0),

    # 16-25: Spaces, Non-Breaking Spaces, and Separators
    ("regular_space_thousands", "1 250 000", 1.0, 1250000.0),
    ("regular_space_millions", "45 100 500", 1.0, 45100500.0),
    ("nbsp_thousands", "1\u00a0250\u00a0000", 1.0, 1250000.0),
    ("narrow_nbsp_thousands", "5\u202f500\u202f000", 1.0, 5500000.0),
    ("mixed_spaces", "12 \u00a0 345 \u202f 678", 1.0, 12345678.0),
    ("leading_trailing_spaces", "   980 000   ", 1.0, 980000.0),
    ("decimal_comma_single_digit", "12,5", 1.0, 12.5),
    ("decimal_comma_multi_digit", "1250,75", 1.0, 1250.75),
    ("decimal_point_only", "1250.75", 1.0, 1250.75),
    ("period_thousands_comma_decimal", "1.250.500,50", 1.0, 1250500.5),

    # 26-35: Negative Formats
    ("parentheses_simple", "(25000)", 1.0, -25000.0),
    ("parentheses_with_space", "( 25 000 )", 1.0, -25000.0),
    ("standard_minus_prefix", "-15000", 1.0, -15000.0),
    ("standard_minus_prefix_spaced", "- 15 000", 1.0, -15000.0),
    ("unicode_minus_sign", "−45000", 1.0, -45000.0),
    ("en_dash_negative", "–12500", 1.0, -12500.0),
    ("em_dash_negative", "—12500", 1.0, -12500.0),
    ("trailing_minus_norwegian", "50000-", 1.0, -50000.0),
    ("negative_with_decimal_comma", "-12,8", 1.0, -12.8),
    ("negative_parentheses_decimal", "(1 450,25)", 1.0, -1450.25),

    # 36-45: Scaling - Base NOK & Thousands (x1,000)
    ("thousands_header_int", 250, 1000.0, 250000.0),
    ("thousands_header_str", "250", 1000.0, 250000.0),
    ("thousands_header_with_space", "1 500", 1000.0, 1500000.0),
    ("thousands_header_negative", "(450)", 1000.0, -450000.0),
    ("thousands_header_decimal", "12,5", 1000.0, 12500.0),
    ("thousands_large_operating", "120 400", 1000.0, 120400000.0),
    ("thousands_small_revenue", "50", 1000.0, 50000.0),
    ("thousands_zero_is_zero", "0", 1000.0, 0.0),
    ("thousands_dash_is_none", "-", 1000.0, None),
    ("thousands_unicode_minus", "−120", 1000.0, -120000.0),

    # 46-55: Scaling - Millions (MNOK x1,000,000)
    ("millions_single_digit", "5", 1000000.0, 5000000.0),
    ("millions_decimal_comma", "12,5", 1000000.0, 12500000.0),
    ("millions_decimal_three_places", "1,234", 1000000.0, 1234000.0),
    ("millions_large_revenue", "450", 1000000.0, 450000000.0),
    ("millions_negative_parentheses", "(2,8)", 1000000.0, -2800000.0),
    ("millions_negative_minus", "-0,5", 1000000.0, -500000.0),
    ("millions_zero_is_zero", "0", 1000000.0, 0.0),
    ("millions_none_is_none", None, 1000000.0, None),
    ("millions_empty_is_none", "", 1000000.0, None),
    ("millions_trailing_minus", "14,2-", 1000000.0, -14200000.0),

    # 56-65: Scaling - Billions (BNOK x1,000,000,000)
    ("billions_int", 2, 1000000000.0, 2000000000.0),
    ("billions_decimal", "3,45", 1000000000.0, 3450000000.0),
    ("billions_equinor_scale", "120,5", 1000000000.0, 120500000000.0),
    ("billions_negative", "(1,2)", 1000000000.0, -1200000000.0),
    ("billions_zero", "0", 1000000000.0, 0.0),
    ("billions_none", "-", 1000000000.0, None),
    ("large_raw_integer", 12345678901, 1.0, 12345678901.0),
    ("large_raw_string", "12 345 678 901", 1.0, 12345678901.0),
    ("norwegian_word_ingen_is_none", "ingen", 1.0, None),
    ("norwegian_word_ikke_oppgitt_is_none", "ikke oppgitt", 1.0, None),
]


@pytest.mark.parametrize("case_id,raw,scale,expected", PARSER_TEST_CASES, ids=lambda c: c[0] if isinstance(c, tuple) else "")
def test_parse_norwegian_number_cases(case_id: str, raw: any, scale: float, expected: float | None) -> None:
    result = parse_norwegian_number(raw, scale_multiplier=scale)
    if expected is None:
        assert result is None, f"Case {case_id}: expected None, got {result}"
    else:
        assert result is not None, f"Case {case_id}: expected {expected}, got None"
        assert pytest.approx(result, rel=1e-5) == expected, f"Case {case_id}: expected {expected}, got {result}"


SCALE_DETECTION_CASES = [
    ("i hele tusen", 1000.0),
    ("Tall i hele tusen kroner", 1000.0),
    ("Beloep i hele 1 000 NOK", 1000.0),
    ("Resultatregnskap (tkr)", 1000.0),
    ("Belop i t.kr", 1000.0),
    ("knok", 1000.0),
    ("i millioner", 1000000.0),
    ("Belop i mill. nok", 1000000.0),
    ("MNOK", 1000000.0),
    ("Tall i MNOK", 1000000.0),
    ("i milliarder", 1000000000.0),
    ("BNOK", 1000000000.0),
    ("i mrd nok", 1000000000.0),
    ("Vanlige kroner uten multiplikator", 1.0),
    ("", 1.0),
]


@pytest.mark.parametrize("header_text,expected_scale", SCALE_DETECTION_CASES)
def test_scale_detection(header_text: str, expected_scale: float) -> None:
    assert detect_scale_factor(header_text) == expected_scale


def test_statement_normalization_multi_year_and_completeness() -> None:
    """Test full financial statement normalization with missing fields preserved."""
    statement_2024 = {
        "id": 10001,
        "regnskapstype": "SELSKAP",
        "regnskapsperiode": "2024-01-01 - 2024-12-31",
        "valuta": "NOK",
        "scale": "Tall i hele tusen NOK",
        "resultatregnskapResultat": {
            "driftsresultat": {
                "driftsinntekter": {
                    "sumDriftsinntekter": "54 200",  # 54 200 tkr = 54 200 000 NOK
                },
                "driftsresultat": "(1 500)",         # (1 500) tkr = -1 500 000 NOK
            },
            "ordinaertResultatFoerSkattekostnad": "-",  # Missing -> None
            "aarsresultat": "0",                     # Zero -> 0.0
        },
        "eiendeler": {
            "sumEiendeler": "35 000",                # 35 000 tkr = 35 000 000 NOK
        },
        "egenkapitalGjeld": {
            "egenkapital": {
                "sumEgenkapital": "15 000",          # 15 000 tkr = 15 000 000 NOK
            },
            "gjeldOversikt": {
                "sumGjeld": None,                    # None -> None
            },
        },
    }

    normalized = normalize_financial_statement(statement_2024)

    assert normalized["revenue"] == 54_200_000.0
    assert normalized["operating_result"] == -1_500_000.0
    assert normalized["profit_before_tax"] is None  # Dash preserved as None
    assert normalized["annual_result"] == 0.0       # Zero preserved as 0.0
    assert normalized["assets"] == 35_000_000.0
    assert normalized["equity"] == 15_000_000.0
    assert normalized["debt"] is None              # None preserved as None
    assert normalized["currency"] == "NOK"
    assert normalized["reporting_period"] == "2024-01-01 - 2024-12-31"
