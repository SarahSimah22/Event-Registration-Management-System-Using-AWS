import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from app import lambda_handler


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self._send_response(200, {})

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def _handle_request(self):
        parsed = urlparse(self.path)
        path = parsed.path
        print(f"Incoming request: {self.command} {path}")

        if self.command == "GET" and (path == "/" or path == ""):
            return self._serve_index()

        event = {
            "httpMethod": self.command,
            "path": path,
            "rawPath": path,
            "body": self._read_body(),
            "requestContext": {"http": {"method": self.command}},
        }
        response = lambda_handler(event, None)
        self._send_response(response.get("statusCode", 200), response)

    def _serve_index(self):
        current_dir = os.path.dirname(__file__)
        site_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
        index_path = os.path.join(site_dir, "index.html")

        if not os.path.exists(index_path):
            self._send_response(404, {"error": "Homepage not found"})
            return

        with open(index_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return None
        return self.rfile.read(length).decode("utf-8")

    def _send_response(self, status_code, response):
        body = response.get("body", "") if isinstance(response, dict) else ""
        payload = body.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), Handler)
    print("Backend running at http://127.0.0.1:8000")
    server.serve_forever()
