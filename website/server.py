#!/usr/bin/env python3
"""
AI Governance MCP Server — Web UI Server
Simple HTTP server for the audit dashboard.
"""
import http.server
import os
import sys

PORT = int(os.environ.get("WEB_UI_PORT", "8080"))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    print(f"AI Governance Web UI: http://localhost:{PORT}")
    print(f"Serving from: {DIRECTORY}")
    http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
