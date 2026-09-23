"""Unit tests for URL safety, SSRF blocking, and scheme validation."""

import unittest
from signalpost.security.network import assert_public_url, canonicalize_url


class SecuritySsrfTests(unittest.TestCase):
    def test_allowed_public_urls(self):
        # Should not raise exception
        assert_public_url("https://www.brreg.no", resolve_dns=False)
        assert_public_url("http://example.no/about", resolve_dns=False)
        assert_public_url("https://builderr.ai/challenges/signalpost", resolve_dns=False)

    def test_forbidden_schemes(self):
        for bad_url in [
            "file:///etc/passwd",
            "ftp://ftp.secret.org",
            "gopher://gopher.example.com",
            "data:text/plain;base64,SGVsbG8=",
            "javascript:alert(1)",
        ]:
            with self.assertRaises(ValueError):
                assert_public_url(bad_url, resolve_dns=False)

    def test_forbidden_hostnames_and_ips(self):
        for restricted_url in [
            "http://localhost:8080/admin",
            "http://127.0.0.1/status",
            "http://[::1]/internal",
            "http://169.254.169.254/latest/meta-data/",  # Cloud metadata service
            "http://10.0.0.5/api",                       # RFC1918 Private class A
            "http://192.168.1.1/router",                 # RFC1918 Private class C
            "http://172.16.0.10/secrets",                # RFC1918 Private class B
            "http://server.local/dashboard",             # Internal .local
            "http://backend.internal/db",                # Internal .internal
        ]:
            with self.assertRaises(ValueError):
                assert_public_url(restricted_url, resolve_dns=False)

    def test_embedded_credentials_are_rejected(self):
        with self.assertRaises(ValueError):
            assert_public_url("https://user:password@example.com", resolve_dns=False)

    def test_canonicalize_url_strips_tracking(self):
        url = "https://example.no/om-oss?utm_source=google&utm_campaign=brand&ref=homepage&id=123"
        clean = canonicalize_url(url)
        self.assertNotIn("utm_source", clean)
        self.assertNotIn("utm_campaign", clean)
        self.assertNotIn("ref", clean)
        self.assertIn("id=123", clean)
