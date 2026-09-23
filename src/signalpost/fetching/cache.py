"""SHA-256 content-addressed on-disk HTTP response cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from signalpost.security.network import canonicalize_url


@dataclass
class CachedResponse:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    body_bytes: bytes
    retrieved_at: str
    content_sha256: str
    elapsed_ms: int = 0


class ResponseCache:
    def __init__(self, cache_dir: Path | str = "data/cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        canon = canonicalize_url(url)
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()

    def get(self, url: str) -> CachedResponse | None:
        key = self._key(url)
        meta_path = self.cache_dir / f"{key}.json"
        body_path = self.cache_dir / f"{key}.body"

        if not meta_path.exists() or not body_path.exists():
            return None

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            body = body_path.read_bytes()
            return CachedResponse(
                url=meta["url"],
                final_url=meta.get("final_url", meta["url"]),
                status=meta["status"],
                headers=meta.get("headers", {}),
                body_bytes=body,
                retrieved_at=meta["retrieved_at"],
                content_sha256=meta["content_sha256"],
                elapsed_ms=0,
            )
        except Exception:
            return None

    def put(
        self,
        url: str,
        status: int,
        headers: dict[str, str],
        body_bytes: bytes,
        retrieved_at: str,
        final_url: str = "",
    ) -> CachedResponse:
        key = self._key(url)
        content_sha256 = hashlib.sha256(body_bytes).hexdigest()

        meta = {
            "url": url,
            "final_url": final_url or url,
            "status": status,
            "headers": dict(headers),
            "retrieved_at": retrieved_at,
            "content_sha256": content_sha256,
            "content_length": len(body_bytes),
        }

        meta_path = self.cache_dir / f"{key}.json"
        body_path = self.cache_dir / f"{key}.body"

        temp_meta = meta_path.with_suffix(".tmp")
        temp_body = body_path.with_suffix(".tmp")

        temp_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        temp_body.write_bytes(body_bytes)

        temp_meta.replace(meta_path)
        temp_body.replace(body_path)

        return CachedResponse(
            url=url,
            final_url=final_url or url,
            status=status,
            headers=headers,
            body_bytes=body_bytes,
            retrieved_at=retrieved_at,
            content_sha256=content_sha256,
            elapsed_ms=0,
        )
