"""Conservative extraction of dated company-owned public activity."""

from __future__ import annotations

import re
import urllib.parse
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

ARTICLE_TYPES = {"NewsArticle", "Article", "BlogPosting", "PressRelease"}
MONTHS = {
    "jan": 1, "januar": 1, "feb": 2, "februar": 2, "mar": 3, "mars": 3,
    "apr": 4, "april": 4, "mai": 5, "jun": 6, "juni": 6, "jul": 7, "juli": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10, "nov": 11, "november": 11, "des": 12, "desember": 12,
}


def _date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date().isoformat()
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})[.\s]+([A-Za-zÆØÅæøå]+)[.\s,]+(20\d{2})\b", text)
    if m:
        mon = MONTHS.get(m.group(2).casefold().rstrip("."))
        if mon:
            try:
                return datetime(int(m.group(3)), mon, int(m.group(1))).date().isoformat()
            except ValueError:
                return None
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(20\d{2})\b", text)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date().isoformat()
        except ValueError:
            return None
    return None


def extract_activity_from_jsonld(data: Any, base_url: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            typ = node.get("@type")
            types = set(typ if isinstance(typ, list) else [typ])
            if types & ARTICLE_TYPES:
                title = str(node.get("headline") or node.get("name") or "").strip()
                published = _date(node.get("datePublished") or node.get("dateCreated"))
                raw_url = node.get("url") or node.get("mainEntityOfPage")
                if isinstance(raw_url, dict):
                    raw_url = raw_url.get("@id") or raw_url.get("url")
                url = urllib.parse.urljoin(base_url, str(raw_url or "").strip()) if (raw_url or base_url) else ""
                if title and published and url:
                    out.append({"title": title[:300], "publication_date": published, "url": url, "category": "company_update"})
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(data)
    return _dedupe(out)


def extract_activity_from_html(html: str, base_url: str = "") -> list[dict[str, Any]]:
    soup = BeautifulSoup(html or "", "html.parser")
    out: list[dict[str, Any]] = []
    # Listing cards and article elements. Require both a real link and an explicit date.
    selectors = "article, li[class*='news'], div[class*='news'], div[class*='post'], div[class*='article'], div[class*='card']"
    for el in soup.select(selectors)[:80]:
        a = el.find("a", href=True)
        if not a:
            continue
        title_el = el.find(["h1", "h2", "h3", "h4"]) or a
        title = title_el.get_text(" ", strip=True)
        if len(title) < 6 or len(title) > 300:
            continue
        time_el = el.find("time")
        date_text = (time_el.get("datetime") if time_el else None) or (time_el.get_text(" ", strip=True) if time_el else None) or el.get_text(" ", strip=True)
        published = _date(date_text)
        if not published:
            continue
        url = urllib.parse.urljoin(base_url, a.get("href"))
        if not url.startswith(("http://", "https://")):
            continue
        out.append({"title": title[:300], "publication_date": published, "url": url, "category": "company_update"})
    # Single article pages often expose a canonical headline/date rather than cards.
    if not out:
        title_el = soup.find("h1")
        date_meta = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find("meta", attrs={"name": "date"})
        published = _date(date_meta.get("content") if date_meta else "") or _date(soup.get_text(" ", strip=True)[:2000])
        canonical = soup.find("link", rel="canonical")
        url = urllib.parse.urljoin(base_url, canonical.get("href") if canonical else base_url)
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if title and published and url:
            out.append({"title": title[:300], "publication_date": published, "url": url, "category": "company_update"})
    return _dedupe(out)


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = (str(item.get("url") or ""), str(item.get("publication_date") or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:20]
