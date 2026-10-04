from __future__ import annotations

from signalpost.discovery.website_discovery import generate_domain_candidates
from signalpost.extraction.activity import extract_activity_from_html, extract_activity_from_jsonld
from signalpost.extraction.jobs import extract_jobs_from_html, extract_jobs_from_jsonld


def test_domain_candidates_normalize_norwegian_name():
    urls = generate_domain_candidates("SANDNES ELEKTRISKE AS", "Sandnes")
    assert "https://sandneselektriske.no" in urls


def test_domain_candidates_strip_city_suffix():
    urls = generate_domain_candidates("HØYER TRONDHEIM AS", "Trondheim")
    assert any("hoyer.no" in u for u in urls)


def test_activity_html_requires_date_and_link():
    html = """
    <article>
      <h2><a href="/nyheter/lansering">Ny produktlansering</a></h2>
      <time datetime="2026-10-01">1. oktober 2026</time>
    </article>
    """
    rows = extract_activity_from_html(html, "https://example.no/nyheter/")
    assert len(rows) == 1
    assert rows[0]["publication_date"] == "2026-10-01"
    assert rows[0]["url"] == "https://example.no/nyheter/lansering"


def test_activity_html_rejects_undated_card():
    html = '<article><h2><a href="/nyheter/x">Generic update</a></h2></article>'
    assert extract_activity_from_html(html, "https://example.no") == []


def test_activity_jsonld_extracts_dated_article():
    rows = extract_activity_from_jsonld([{
        "@type": "NewsArticle",
        "headline": "Verified company update",
        "datePublished": "2026-09-30T09:00:00+02:00",
        "url": "/news/update",
    }], "https://example.no")
    assert rows == [{
        "title": "Verified company update",
        "publication_date": "2026-09-30",
        "url": "https://example.no/news/update",
        "category": "company_update",
    }]


def test_job_jsonld_rejects_expired_posting():
    rows = extract_jobs_from_jsonld([{
        "@type": "JobPosting",
        "title": "Old role",
        "validThrough": "2020-01-01",
        "url": "https://example.no/jobs/old",
    }])
    assert rows == []


def test_job_link_extraction_finds_specific_vacancy():
    html = '<a href="/ledig-stilling-elektriker">Vi søker elektriker</a>'
    rows = extract_jobs_from_html(html, "https://example.no/ledige-stillinger")
    assert len(rows) == 1
    assert rows[0]["url"] == "https://example.no/ledig-stilling-elektriker"


def test_job_link_extraction_rejects_careers_landing_link():
    html = '<a href="/karriere">Karriere</a>'
    assert extract_jobs_from_html(html, "https://example.no") == []
