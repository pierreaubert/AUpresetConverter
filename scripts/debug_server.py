#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """Generate CORS headers"""

    def do_GET(self):  # noqa: N802
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super(CORSRequestHandler, self).end_headers()


if __name__ == "__main__":
    ip = "127.0.0.1"
    port = 7999

    try:
        httpd = HTTPServer((ip, port), CORSRequestHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("... Bye")
        sys.exit(0)
    sys.exit(1)
