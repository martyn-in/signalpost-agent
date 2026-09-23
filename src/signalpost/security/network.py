"""Network security controls, safe URL validation, and SSRF prevention."""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse

BLOCKED_DOMAINS = {
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "::1",
    "metadata.google.internal",
    "instance-data",
}

BLOCKED_SUFFIXES = (
    ".local",
    ".internal",
    ".lan",
    ".corp",
    ".test",
    ".example",
    ".invalid",
)

TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "_hsenc",
    "_hsmi",
    "ref",
}


def is_restricted_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if an IP belongs to private, loopback, link-local or reserved ranges."""
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        # Explicit check for 169.254.0.0/16 cloud metadata service
        or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.IPv4Network("169.254.0.0/16"))
        or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.IPv4Network("100.64.0.0/10"))  # Carrier-grade NAT
    )


def assert_public_url(url: str, resolve_dns: bool = True) -> None:
    """Validate that a URL is a safe public HTTP/HTTPS endpoint.
    
    Raises ValueError if the URL violates scheme, credential, or SSRF security boundaries.
    """
    if not url or not isinstance(url, str):
        raise ValueError(f"Invalid URL: {url!r}")

    parsed = urllib.parse.urlsplit(url.strip())

    # 1. Scheme check
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError(f"Scheme not permitted: {parsed.scheme!r} in {url}")

    # 2. Embedded credentials check
    if parsed.username or parsed.password:
        raise ValueError(f"URL containing credentials is not permitted: {url}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"URL missing hostname: {url}")

    hostname_clean = hostname.strip("[]").casefold()

    # 3. Blocked domain and suffix checks
    if hostname_clean in BLOCKED_DOMAINS:
        raise ValueError(f"SSRF blocked: forbidden host {hostname_clean!r}")

    if any(hostname_clean.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
        raise ValueError(f"SSRF blocked: internal domain suffix in {hostname_clean!r}")

    # 4. Check if hostname is an IP literal
    ip = None
    try:
        ip = ipaddress.ip_address(hostname_clean)
    except ValueError:
        pass  # Not an IP literal, proceed to DNS resolution if requested

    if ip is not None:
        if is_restricted_ip(ip):
            raise ValueError(f"SSRF blocked: IP {ip} is in restricted range")
        return

    # 5. DNS resolution check to prevent DNS rebinding to private IPs
    if resolve_dns:
        try:
            addr_info = socket.getaddrinfo(hostname_clean, None, proto=socket.IPPROTO_TCP)
            for item in addr_info:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                if is_restricted_ip(ip):
                    raise ValueError(f"SSRF blocked: {hostname_clean} resolves to restricted IP {ip}")
        except socket.gaierror:
            # If DNS fails here, let the HTTP client handle DNS failure downstream
            pass


def canonicalize_url(url: str) -> str:
    """Normalize a URL by sorting query params, stripping tracking tokens, and standardizing ports."""
    parsed = urllib.parse.urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove standard ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Filter out tracking query parameters
    query_items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    filtered_queries = [
        (k, v) for k, v in query_items
        if k.lower() not in TRACKING_QUERY_PARAMS and not k.lower().startswith("utm_")
    ]
    new_query = urllib.parse.urlencode(sorted(filtered_queries))

    path = parsed.path or "/"
    # Clean up double slashes in path
    while "//" in path:
        path = path.replace("//", "/")

    return urllib.parse.urlunsplit((scheme, netloc, path, new_query, ""))
