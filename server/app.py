#!/usr/bin/env python3
"""
Minimal upload sink service for network tests.

Endpoints:
- GET /health -> 200 "ok"
- POST/PUT/PATCH /up -> reads request body fully, discards it, returns 204
"""

from __future__ import annotations

import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "65536"))
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "0"))


class UploadSinkHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "upload-sink/1.0"

    def do_GET(self) -> None:
        if self._path() == "/health":
            self._send_text(HTTPStatus.OK, "ok\n")
            return
        self._send_text(HTTPStatus.NOT_FOUND, "not found\n")

    def do_POST(self) -> None:
        self._handle_upload()

    def do_PUT(self) -> None:
        self._handle_upload()

    def do_PATCH(self) -> None:
        self._handle_upload()

    def do_DELETE(self) -> None:
        self._send_text(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed\n")

    def do_HEAD(self) -> None:
        if self._path() == "/health":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _path(self) -> str:
        return urlsplit(self.path).path

    def _handle_upload(self) -> None:
        if self._path() != "/up":
            self._send_text(HTTPStatus.NOT_FOUND, "not found\n")
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_text(HTTPStatus.LENGTH_REQUIRED, "content-length required\n")
            return

        try:
            remaining = int(content_length)
        except ValueError:
            self._send_text(HTTPStatus.BAD_REQUEST, "invalid content-length\n")
            return

        if remaining < 0:
            self._send_text(HTTPStatus.BAD_REQUEST, "invalid content-length\n")
            return

        received = 0
        start = time.perf_counter()

        while remaining > 0:
            chunk = self.rfile.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                self._send_text(HTTPStatus.BAD_REQUEST, "incomplete body\n")
                return
            received += len(chunk)
            remaining -= len(chunk)

            if MAX_BODY_BYTES > 0 and received > MAX_BODY_BYTES:
                self._send_text(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "payload too large\n"
                )
                return

        elapsed = time.perf_counter() - start
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.send_header("X-Bytes-Received", str(received))
        self.send_header("X-Elapsed-Seconds", f"{elapsed:.6f}")
        self.end_headers()
        self.log_message("upload complete bytes=%d elapsed=%.3fs", received, elapsed)

    def _send_text(self, status: HTTPStatus, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
        super().log_message(fmt, *args)


def main() -> None:
    if CHUNK_SIZE <= 0:
        raise ValueError("CHUNK_SIZE must be greater than 0")
    if PORT <= 0 or PORT > 65535:
        raise ValueError("PORT must be in range 1..65535")

    server = ThreadingHTTPServer((HOST, PORT), UploadSinkHandler)
    print(f"upload-sink listening on {HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
