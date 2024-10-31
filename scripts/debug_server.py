#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import http.server
import http.client

TARGET_SERVER='0.0.0.0'
TARGET_PORT=8000

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request('GET')

    def do_POST(self):
        self.handle_request('POST')

    def do_PUT(self):
        self.handle_request('PUT')

    def do_DELETE(self):
        self.handle_request('DELETE')

    def do_HEAD(self):
        self.handle_request('HEAD')

    def proxy_request(self, method):
        # Open a connection to the target server
        conn = http.client.HTTPConnection(TARGET_SERVER, TARGET_PORT)
        # Send the original request to the target server with all headers
        conn.request(method, self.path, headers=self.headers)
        # Get the response from the target server
        response = conn.getresponse()
        # Send the target server's response back to the client
        self.send_response(response.status)
        for header, value in response.getheaders():
            self.send_header(header, value)
        # add cors headers
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(response.read())
        conn.close()

    def read_file(self, path):
        try:
            filename = path[1:]
            if path == '/':
                filename = 'index.html'
            with open(filename, "r") as fd:
                text = fd.read().encode(encoding='utf-8')
                self.send_response(200)
                suffix='html'
                if len(filename)>5:
                    if filename[-3:] == 'xml':
                        suffix = 'xml'
                    elif filename[-2:] == 'js':
                        suffix = 'javascript'
                self.send_header('Content-type', 'text/{}'.format(suffix))
                self.end_headers()
                self.flush_headers()
                # Send the html message
                self.wfile.write(text)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def handle_request(self, method):
        path = self.path
        if path[0:3] == '/v1':
            self.proxy_request(method)
        else:
            self.read_file(path)



if __name__ == "__main__":
    ip = "127.0.0.1"
    port = 7999

    try:
        httpd = http.server.ThreadingHTTPServer((ip, port), ProxyHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("... Bye")
        sys.exit(0)
    sys.exit(1)
