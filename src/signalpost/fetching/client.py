"""Async and synchronous safe HTTP client with SSRF protection, caching, and budget tracking."""

from __future__ import annotations

import datetime
import hashlib
import time
from typing import Any
import httpx

from signalpost.config import settings
from signalpost.fetching.budget import RequestBudget
from signalpost.fetching.cache import ResponseCache
from signalpost.security.network import assert_public_url


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class FetchResponse:
    def __init__(
        self,
        url: str,
        final_url: str,
        status_code: int,
        headers: dict[str, str],
        body_bytes: bytes,
        retrieved_at: str,
        elapsed_ms: int = 0,
        error: str | None = None,
        cached: bool = False,
    ) -> None:
        self.url = url
        self.final_url = final_url
        self.status_code = status_code
        self.headers = headers
        self.body_bytes = body_bytes
        self.retrieved_at = retrieved_at
        self.elapsed_ms = elapsed_ms
        self.error = error
        self.cached = cached
        self.content_sha256 = hashlib.sha256(body_bytes).hexdigest()

    @property
    def text(self) -> str:
        try:
            return self.body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return self.body_bytes.decode("latin-1", errors="replace")

    def json(self) -> Any:
        import json
        return json.loads(self.text)


class SafeHttpClient:
    def __init__(
        self,
        budget: RequestBudget | None = None,
        cache: ResponseCache | None = None,
    ) -> None:
        self.budget = budget or RequestBudget()
        self.cache = cache or ResponseCache()

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        priority: str = "normal",
        use_cache: bool = True,
        max_retries: int = 1,
    ) -> FetchResponse:
        """Synchronous safe GET request."""
        # 1. SSRF and public URL validation
        try:
            assert_public_url(url)
        except ValueError as exc:
            return FetchResponse(
                url=url,
                final_url=url,
                status_code=400,
                headers={},
                body_bytes=b"",
                retrieved_at=utc_now(),
                error=f"Security rejection: {exc}",
            )

        # 2. Check cache
        if use_cache:
            cached = self.cache.get(url)
            if cached:
                self.budget.record_cache_hit(len(cached.body_bytes))
                return FetchResponse(
                    url=cached.url,
                    final_url=cached.final_url,
                    status_code=cached.status,
                    headers=cached.headers,
                    body_bytes=cached.body_bytes,
                    retrieved_at=cached.retrieved_at,
                    elapsed_ms=0,
                    cached=True,
                )

        # 3. Check budget
        if not self.budget.can_request(priority):
            return FetchResponse(
                url=url,
                final_url=url,
                status_code=429,
                headers={},
                body_bytes=b"",
                retrieved_at=utc_now(),
                error="Budget limit reached",
            )

        req_headers = {"User-Agent": settings.user_agent, "Accept": "*/*"}
        if headers:
            req_headers.update(headers)

        retries = 0
        current_url = url

        while True:
            start_time = time.monotonic()
            retrieved_at = utc_now()
            try:
                self.budget.record_request(is_retry=(retries > 0))
                with httpx.Client(
                    timeout=httpx.Timeout(
                        connect=settings.timeout_connect,
                        read=settings.timeout_read,
                        write=settings.timeout_read,
                        pool=settings.timeout_total,
                    ),
                    follow_redirects=False,
                ) as client:
                    resp = client.get(current_url, headers=req_headers)
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)

                    # Handle redirects with per-hop SSRF validation
                    if resp.is_redirect and "location" in resp.headers:
                        redirect_url = resp.headers["location"]
                        import urllib.parse
                        redirect_url = urllib.parse.urljoin(current_url, redirect_url)
                        assert_public_url(redirect_url)
                        self.budget.record_request(is_redirect=True)
                        current_url = redirect_url
                        continue

                    body = resp.content[: settings.max_body_bytes]
                    fetch_resp = FetchResponse(
                        url=url,
                        final_url=str(resp.url),
                        status_code=resp.status_code,
                        headers=dict(resp.headers),
                        body_bytes=body,
                        retrieved_at=retrieved_at,
                        elapsed_ms=elapsed_ms,
                    )

                    # Cache successful or definitive responses
                    if use_cache and resp.status_code in {200, 404, 410}:
                        self.cache.put(
                            url=url,
                            status=resp.status_code,
                            headers=dict(resp.headers),
                            body_bytes=body,
                            retrieved_at=retrieved_at,
                            final_url=str(resp.url),
                        )

                    return fetch_resp

            except Exception as exc:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                if retries < max_retries and self.budget.can_request(priority):
                    retries += 1
                    time.sleep(0.5)
                    continue

                return FetchResponse(
                    url=url,
                    final_url=current_url,
                    status_code=500,
                    headers={},
                    body_bytes=b"",
                    retrieved_at=retrieved_at,
                    elapsed_ms=elapsed_ms,
                    error=str(exc),
                )
