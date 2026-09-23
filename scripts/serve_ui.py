#!/usr/bin/env python3
"""Lightweight local web server for Signalpost verification showcase."""

import http.server
import socketserver
import sys
from pathlib import Path

PORT = 8080
DIRECTORY = Path(__file__).resolve().parents[1] / "out"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)


def main() -> None:
    showcase = DIRECTORY / "showcase.html"
    if not showcase.exists():
        print(f"showcase.html not found in {DIRECTORY}. Run build_prototype.py first.", file=sys.stderr)
        sys.exit(1)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving Signalpost Verification Showcase at http://localhost:{PORT}/showcase.html")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
