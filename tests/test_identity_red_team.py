"""Adversarial Identity Red Team Suite (40+ Scenarios).

Tests company identity resolution and website verification against 40+ adversarial cases:
- Conflicting organisation numbers
- Same name, different city / industry
- Foreign namesakes (UK Ltd, Delaware LLC, GmbH, AB)
- Parked, for-sale, and generic placeholder domains
- Aggregators, directory sites, job boards (Finn.no, Proff, LinkedIn)
- Brand vs legal entity ambiguity
- Parent vs subsidiary / subsidiary vs parent
- Subunit / branch vs head entity
- Umbrella domains without exact entity linkage
- Social media profiles, blog mentions, news articles
- Shared hosting / multiple org numbers in footer
- Parked/expired domains

Target: 0 known material wrong-company publications.
"""

from __future__ import annotations

import pytest
from signalpost.identity.resolver import assess_website_identity
from norway_company_agent.identity import assess_website_identity as assess_agent_identity


# =========================================================================
# 42 Adversarial Test Fixtures
# =========================================================================
ADVERSARIAL_CASES = [
    # 1-5: Conflicting Organisation Numbers
    {
        "id": "conflicting_org_in_footer",
        "company_name": "Fjord Seafood AS",
        "org_number": "912345678",
        "page": {
            "title": "Fjord Seafood AS",
            "text": "Velkommen til Fjord Seafood. Org.nr: 987654321 MVA.",
        },
        "expected_publishable": False,
        "description": "Footer contains a completely different Norwegian org number",
    },
    {
        "id": "conflicting_org_spaced",
        "company_name": "Bergen Logistics AS",
        "org_number": "911222333",
        "page": {
            "title": "Bergen Logistics",
            "text": "Kontakt oss: Organisasjonsnummer 999 888 777",
        },
        "expected_publishable": False,
        "description": "Conflicting org number formatted with spaces",
    },
    {
        "id": "multiple_conflicting_orgs",
        "company_name": "Nordic Tech AS",
        "org_number": "911111111",
        "page": {
            "title": "Nordic Tech Group",
            "text": "Driftes av Selskap A (922222222) og Selskap B (933333333).",
        },
        "expected_publishable": False,
        "description": "Multiple third-party org numbers, target absent",
    },
    {
        "id": "similar_org_transposed_digits",
        "company_name": "Stavanger Olje AS",
        "org_number": "987654321",
        "page": {
            "title": "Stavanger Olje AS",
            "text": "Org nr: 987654312",
        },
        "expected_publishable": False,
        "description": "Transposed digits in organisation number",
    },
    {
        "id": "target_absent_competitor_org_present",
        "company_name": "Oslo Bakeri AS",
        "org_number": "920102030",
        "page": {
            "title": "Bakerier i Oslo",
            "text": "Besøk også Vika Bakeri AS, org nr 940506070.",
        },
        "expected_publishable": False,
        "description": "Competitor bakery org number on directory page",
    },

    # 6-10: Foreign Namesakes & International Entities
    {
        "id": "uk_ltd_namesake",
        "company_name": "Apex Consulting AS",
        "org_number": "912345671",
        "page": {
            "title": "Apex Consulting Ltd",
            "description": "UK Management Consultants",
            "text": "Registered in England and Wales company no 08123456. London EC1.",
        },
        "expected_publishable": False,
        "description": "UK company with identical stem name",
    },
    {
        "id": "us_delaware_llc",
        "company_name": "Viking Software AS",
        "org_number": "912345672",
        "page": {
            "title": "Viking Software LLC",
            "description": "US Delaware entity",
            "text": "Incorporated in Delaware. Silicon Valley office.",
        },
        "expected_publishable": False,
        "description": "US LLC with same name",
    },
    {
        "id": "german_gmbh_namesake",
        "company_name": "Solar Kraft AS",
        "org_number": "912345673",
        "page": {
            "title": "Solar Kraft GmbH",
            "text": "Handelsregister München HRB 12345. Alle Rechte vorbehalten.",
        },
        "expected_publishable": False,
        "description": "German GmbH with German registry notice",
    },
    {
        "id": "swedish_ab_namesake",
        "company_name": "Nordic Bio AS",
        "org_number": "912345674",
        "page": {
            "title": "Nordic Bio AB",
            "text": "Svenskt aktiebolag med säte i Stockholm. Org.nr 556123-4567.",
        },
        "expected_publishable": False,
        "description": "Swedish AB namesake with Swedish 10-digit number",
    },
    {
        "id": "danish_aps_namesake",
        "company_name": "Kattegat Design AS",
        "org_number": "912345675",
        "page": {
            "title": "Kattegat Design ApS",
            "text": "Dansk designbureau i København. CVR-nr: 12345678.",
        },
        "expected_publishable": False,
        "description": "Danish ApS with CVR number",
    },

    # 11-15: Parked, For-Sale, and Generic Placeholder Domains
    {
        "id": "hugedomains_parked",
        "company_name": "Future Mobility AS",
        "org_number": "912345681",
        "page": {
            "title": "futuremobility.no is for sale",
            "text": "Buy this domain at HugeDomains. Fast and easy transfer.",
        },
        "expected_publishable": False,
        "description": "HugeDomains parked sales page",
    },
    {
        "id": "generic_registrar_holding",
        "company_name": "Troms Bygg AS",
        "org_number": "912345682",
        "page": {
            "title": "Parked at Miss Hosting",
            "text": "Her flytter snart en ny gjest inn. Velkommen tilbake senere.",
        },
        "expected_publishable": False,
        "description": "Hosting placeholder landing page",
    },
    {
        "id": "domain_for_sale_sedo",
        "company_name": "Nordic Cloud AS",
        "org_number": "912345683",
        "page": {
            "title": "Nordic Cloud - Domain for Sale",
            "text": "The domain nordiccloud.no may be for sale. Inquire today.",
        },
        "expected_publishable": False,
        "description": "Domain for sale landing page",
    },
    {
        "id": "ad_network_farm",
        "company_name": "Halden Rør AS",
        "org_number": "912345684",
        "page": {
            "title": "Halden Ror - Search Resources",
            "text": "Find the best information and most relevant links on all topics related to plumbing and pipes.",
        },
        "expected_publishable": False,
        "description": "Generic PPC ad farm placeholder",
    },
    {
        "id": "expired_blank_page",
        "company_name": "Telemark Data AS",
        "org_number": "912345685",
        "page": {
            "title": "Index of /",
            "text": "Apache/2.4.41 Server at port 80",
        },
        "expected_publishable": False,
        "description": "Raw web server index without company identity",
    },

    # 16-20: Aggregators, Directories, and Review Portals
    {
        "id": "proff_no_aggregator",
        "company_name": "Bergen VVS AS",
        "org_number": "912345691",
        "page": {
            "title": "Bergen VVS AS - Regnskap og Roller | Proff.no",
            "text": "Proff gir deg bedriftsinformasjon om Bergen VVS AS. Finn roller, eiere og regnskap.",
        },
        "expected_publishable": False,
        "description": "Proff company directory page",
    },
    {
        "id": "gulesider_directory",
        "company_name": "Trondheim Elektro AS",
        "org_number": "912345692",
        "page": {
            "title": "Trondheim Elektro AS - Gule Sider",
            "text": "Gule Sider firmaoversikt for Trondheim Elektro AS.",
        },
        "expected_publishable": False,
        "description": "Gule Sider directory aggregator",
    },
    {
        "id": "finn_no_job_ad",
        "company_name": "Nordic Retail AS",
        "org_number": "912345693",
        "page": {
            "title": "Butikkmedarbeider søkes til Nordic Retail - FINN.no",
            "text": "FINN jobbannonse for stilling hos Nordic Retail. Søk nå via FINN.",
        },
        "expected_publishable": False,
        "description": "Job board portal posting",
    },
    {
        "id": "purehelp_listing",
        "company_name": "Lofoten Fisk AS",
        "org_number": "912345694",
        "page": {
            "title": "Lofoten Fisk AS - Bedriftsinformasjon på Purehelp.no",
            "text": "Purehelp leverer selskapsinformasjon om Lofoten Fisk AS.",
        },
        "expected_publishable": False,
        "description": "Purehelp corporate directory",
    },
    {
        "id": "linkedin_company_profile",
        "company_name": "Innovasjon Norge AS",
        "org_number": "912345695",
        "page": {
            "title": "Innovasjon Norge | LinkedIn",
            "text": "Sign in to LinkedIn to view Innovasjon Norge profile and jobs.",
        },
        "expected_publishable": False,
        "description": "Social network aggregator profile",
    },

    # 21-25: Multi-Tenant & Umbrella Sites
    {
        "id": "umbrella_coworking_space",
        "company_name": "Fintech Alpha AS",
        "org_number": "912345701",
        "page": {
            "title": "Mesh Community - Coworking Space Oslo",
            "text": "Our vibrant community hosts startups like Fintech Alpha, Beta Analytics and Gamma Pay.",
        },
        "expected_publishable": False,
        "description": "Coworking space mentioning tenant company in body copy",
    },
    {
        "id": "parent_umbrella_holding_site",
        "company_name": "Aker Subsea Tech AS",
        "org_number": "912345702",
        "page": {
            "title": "Aker ASA - Global Industrial Investment",
            "text": "Aker ASA is an industrial investment company with ownership in energy and software.",
        },
        "expected_publishable": False,
        "description": "Parent holding company website without subsidiary org number",
    },
    {
        "id": "venture_portfolio_mention",
        "company_name": "CleanTech Solutions AS",
        "org_number": "912345703",
        "page": {
            "title": "Snö Ventures - Portfolio",
            "text": "We back founders transforming industries, including CleanTech Solutions in Oslo.",
        },
        "expected_publishable": False,
        "description": "Venture fund portfolio list",
    },
    {
        "id": "franchise_portal_mismatch",
        "company_name": "Pizza Express Tromsø AS",
        "org_number": "912345704",
        "page": {
            "title": "Pizza Express Norge",
            "text": "Bestill pizza online til alle byer i Norge.",
        },
        "expected_publishable": False,
        "description": "Franchise brand site without specific franchisee legal details",
    },
    {
        "id": "sports_club_vs_corporate_sponsor",
        "company_name": "Equinor Bedriftsidrettslag",
        "org_number": "912345705",
        "page": {
            "title": "Equinor ASA - Official Website",
            "text": "Equinor is an international energy company committed to creating long-term value.",
        },
        "expected_publishable": False,
        "description": "Corporate site for sports club BIL entity",
    },

    # 26-30: News Articles & Press Mentions
    {
        "id": "dn_no_press_article",
        "company_name": "Polar Hydrogen AS",
        "org_number": "912345711",
        "page": {
            "title": "Polar Hydrogen satser milliarder i Nord-Norge | DN.no",
            "text": "Dagens Næringsliv: Gründerne bak Polar Hydrogen forteller om sine nye planer.",
        },
        "expected_publishable": False,
        "description": "Newspaper feature article",
    },
    {
        "id": "e24_stock_ticker_mention",
        "company_name": "Nordic Mining AS",
        "org_number": "912345712",
        "page": {
            "title": "Børsen i dag - E24",
            "text": "Aksjekurs og nyheter for Nordic Mining på Oslo Børs.",
        },
        "expected_publishable": False,
        "description": "Financial news market summary",
    },
    {
        "id": "industry_blog_review",
        "company_name": "Voss Bryggeri AS",
        "org_number": "912345713",
        "page": {
            "title": "Beste håndverksbryggerier på Vestlandet - Ølportalen",
            "text": "Vi testet kveik-øl fra Voss Bryggeri og Kinn.",
        },
        "expected_publishable": False,
        "description": "Consumer hobby blog reviewing products",
    },
    {
        "id": "scientific_paper_citation",
        "company_name": "BioPharma Arctic AS",
        "org_number": "912345714",
        "page": {
            "title": "Marine Bioactive Peptides Research - PubMed",
            "text": "Samples provided in part by BioPharma Arctic AS, Tromsø.",
        },
        "expected_publishable": False,
        "description": "Academic publication acknowledgment",
    },
    {
        "id": "conference_speaker_bio",
        "company_name": "DataGen Analytics AS",
        "org_number": "912345715",
        "page": {
            "title": "JavaZone 2025 Speakers",
            "text": "Kari Nordmann, lead engineer at DataGen Analytics, speaks on concurrency.",
        },
        "expected_publishable": False,
        "description": "Tech conference schedule bio",
    },

    # 31-35: Partial Name Overlaps & Generic Words
    {
        "id": "generic_single_common_token_unsubstantiated",
        "company_name": "Vekst AS",
        "org_number": "912345721",
        "page": {
            "title": "Vekst i norsk næringsliv",
            "text": "Statistikk og analyser.",
        },
        "expected_publishable": False,
        "description": "Single generic token ('vekst') without substantive business evidence",
    },
    {
        "id": "sub_token_partial_overlap",
        "company_name": "Oslo Maritim Elektro Service AS",
        "org_number": "912345722",
        "page": {
            "title": "Oslo Elektro AS",
            "text": "Elektriker i Oslo for private og næring.",
        },
        "expected_publishable": False,
        "description": "Subset of tokens matching different legal entity",
    },
    {
        "id": "inverted_name_tokens_different_firm",
        "company_name": "Hansen & Olsen Bygg AS",
        "org_number": "912345723",
        "page": {
            "title": "Olsen & Hansen Eiendom",
            "text": "Eiendomsmegling i Vestfold.",
        },
        "expected_publishable": False,
        "description": "Inverted names in different line of business",
    },
    {
        "id": "city_and_trade_generic_match",
        "company_name": "Bergen Malerteam AS",
        "org_number": "912345724",
        "page": {
            "title": "Maler i Bergen",
            "text": "Trenger du malerteam i Bergen? Kontakt oss.",
        },
        "expected_publishable": False,
        "description": "Keyword matching SEO lander for painters",
    },
    {
        "id": "holding_suffix_distinction",
        "company_name": "Solheim Invest AS",
        "org_number": "912345725",
        "page": {
            "title": "Solheim Holding AS",
            "text": "Investeringsselskap i Drammen.",
        },
        "expected_publishable": False,
        "description": "Invest vs Holding distinct entity",
    },

    # 36-40: Branch, Former Name, and Discontinued Entities
    {
        "id": "bankrupt_legacy_notice",
        "company_name": "Nordic Timber AS",
        "org_number": "912345731",
        "page": {
            "title": "Nordic Timber AS - Konkursbo",
            "text": "Bostyret melder om avvikling og realisasjon av aktiva for Nordic Timber AS.",
        },
        "expected_publishable": False,
        "description": "Bankruptcy estate liquidation notice",
    },
    {
        "id": "renamed_former_entity_mismatch",
        "company_name": "Vestland Byggservice AS",
        "org_number": "912345732",
        "page": {
            "title": "Gamle Fjord Bygg AS",
            "text": "Tidligere Vestland Byggservice, nå Fjord Bygg.",
        },
        "expected_publishable": False,
        "description": "Historical name match on renamed entity",
    },
    {
        "id": "swedish_parent_with_norwegian_branch",
        "company_name": "Scandia Logistics NUF",
        "org_number": "912345733",
        "page": {
            "title": "Scandia Logistics AB Sverige",
            "text": "Välkommen till Scandia Logistics i Göteborg.",
        },
        "expected_publishable": False,
        "description": "Foreign parent site lacking NUF branch org number",
    },
    {
        "id": "merged_absorbed_firm",
        "company_name": "Kongsberg Våpenteknikk AS",
        "org_number": "912345734",
        "page": {
            "title": "Kongsberg Defence & Aerospace",
            "text": "Virksomheten er fusjonert inn i KDA. Gå til kongsberg.com.",
        },
        "expected_publishable": False,
        "description": "Absorbed legacy entity redirect",
    },
    {
        "id": "job_aggregator_scrape",
        "company_name": "Trondheim Barnehage AS",
        "org_number": "912345735",
        "page": {
            "title": "Stillinger hos Trondheim Barnehage AS - Arbeidsplassen.no",
            "text": "NAV Arbeidsplassen: Ledige stillinger.",
        },
        "expected_publishable": False,
        "description": "NAV state job recruitment board listing",
    },

    # 41-42: Positive Controls (Golden Standards - MUST Pass)
    {
        "id": "positive_control_exact_org_number",
        "company_name": "Sandnes Elektriske AS",
        "org_number": "810034882",
        "page": {
            "title": "Sandnes Elektriske AS - Din lokale elektriker",
            "description": "Autorisert elektroinstallatør i Rogaland",
            "text": "Kontakt oss på post@sandnes-elektriske.no. Org.nr: 810 034 882. Storgata 1, Sandnes.",
        },
        "expected_publishable": True,
        "description": "Positive control: Official website with exact org number in footer",
    },
    {
        "id": "positive_control_multi_token_headers",
        "company_name": "Nordic Innovators AS",
        "org_number": "923609016",
        "page": {
            "title": "Nordic Innovators AS",
            "description": "Research and development consulting services across Scandinavia",
            "text": "Nordic Innovators helps innovative companies obtain EU and national research grants.",
        },
        "expected_publishable": True,
        "description": "Positive control: Exact multi-token legal name in homepage title and description",
    },
]


@pytest.mark.parametrize("case", ADVERSARIAL_CASES, ids=lambda c: c["id"])
def test_adversarial_identity_gate(case: dict) -> None:
    """Run adversarial fixture through the strict identity resolver."""
    assessment = assess_website_identity(
        company_name=case["company_name"],
        target_org_number=case["org_number"],
        page_data=case["page"],
    )

    is_publishable = assessment.get("publishable", False)
    expected = case["expected_publishable"]

    assert is_publishable == expected, (
        f"Case '{case['id']}' failed: expected publishable={expected}, got {is_publishable}. "
        f"Score: {assessment.get('score')}, Status: {assessment.get('status')}, "
        f"Reasons: {assessment.get('reasons')}"
    )
