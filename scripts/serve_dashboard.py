"""Local-only dashboard server with a working Refresh button.

Binds strictly to 127.0.0.1 - never reachable from the phone or any other
device on the network, by design (this project deliberately keeps
credentials and live API calls off any network-reachable surface). Run
this on the Mac when you want the Refresh button on the dashboard to
work; the iCloud-synced copy used on the phone has no server behind it,
so its Refresh button just shows an explanatory message instead.

Usage:
    python -m scripts.serve_dashboard
"""

import http.server
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, PROJECT_ROOT  # noqa: E402
from src.dashboard_render import render_dashboard_html  # noqa: E402

SUMMARY_FILE = DATA_DIR / "summary.json"
PORT = 8787

# A custom header forces the browser to CORS-preflight cross-origin POSTs;
# since we never send Access-Control-Allow-Origin, that preflight fails for
# any origin but this page itself - a lightweight CSRF guard for a server
# that's otherwise trivially reachable by anything running on the same Mac.
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "finance-tracker"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/dashboard.html"):
            self.send_response(404)
            self.end_headers()
            return
        if not SUMMARY_FILE.is_file():
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"Run 'python -m scripts.build_summary' first.")
            return

        html = render_dashboard_html(SUMMARY_FILE.read_text(encoding="utf-8"))
        body = html.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/refresh" or self.headers.get(CSRF_HEADER) != CSRF_VALUE:
            self.send_response(403)
            self.end_headers()
            return

        output = []
        ok = True
        for module in ("scripts.build_summary", "scripts.build_dashboard"):
            result = subprocess.run(
                [sys.executable, "-m", module],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            output.append(result.stdout + result.stderr)
            if result.returncode != 0:
                ok = False
                break

        body = json.dumps({"ok": ok, "output": "\n".join(output)[-3000:]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[serve_dashboard] {format % args}")


def main() -> None:
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Dashboard running at http://127.0.0.1:{PORT}/ (Ctrl+C to stop)")
    print("Bound to 127.0.0.1 only - never reachable from your phone or the network.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
