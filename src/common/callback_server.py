"""Local HTTP(S) listener that catches a single OAuth-style redirect.

Only requests to CALLBACK_PATH are treated as the real redirect; anything
else (browser prefetch pings, connectivity/liveness probes, stray requests
from another app on the same port) is answered and ignored so the listener
keeps waiting for the actual callback.
"""

import http.server
import socket
import ssl
import time
import urllib.parse
from typing import Optional

CALLBACK_PATH = "/callback"
DEFAULT_TIMEOUT_SECONDS = 300


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return

        self.server.callback_params = urllib.parse.parse_qs(parsed.query)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Login received</h1>"
            b"<p>You can close this tab and return to the terminal.</p></body></html>"
        )

    def log_message(self, format, *args):
        return  # silence default request logging, keep terminal output clean


def listen_for_callback(
    port: int,
    ssl_context: Optional[ssl.SSLContext] = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Blocks until a GET request to /callback arrives, ignoring anything else."""
    server = http.server.HTTPServer(("localhost", port), _CallbackHandler)
    server.callback_params = None
    if ssl_context is not None:
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)

    deadline = time.monotonic() + timeout_seconds
    while server.callback_params is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            server.server_close()
            raise TimeoutError("Timed out waiting for the OAuth redirect callback.")
        server.timeout = remaining
        try:
            server.handle_request()
        except (ssl.SSLError, socket.timeout, ConnectionResetError, OSError):
            continue  # incomplete/invalid connection (e.g. a TLS probe) - keep listening

    server.server_close()
    return server.callback_params
