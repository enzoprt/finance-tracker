"""Builds the self-contained dashboard HTML (summary.json embedded inline,
no fetch() needed) and writes it to iCloud Drive so it syncs to the iPhone
automatically. Open it from the Files app in Safari and "Add to Home Screen".

Usage:
    python -m scripts.build_dashboard
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR  # noqa: E402
from src.dashboard_render import render_dashboard_html  # noqa: E402

SUMMARY_FILE = DATA_DIR / "summary.json"

ICLOUD_DIR = Path(
    "~/Library/Mobile Documents/com~apple~cloudDocs/Administratif/Banque et Finance/Finance Tracker"
).expanduser()
OUTPUT_FILE = ICLOUD_DIR / "dashboard.html"


def main() -> None:
    if not SUMMARY_FILE.is_file():
        raise RuntimeError(f"{SUMMARY_FILE} not found - run `python -m scripts.build_summary` first.")

    html = render_dashboard_html(SUMMARY_FILE.read_text(encoding="utf-8"))

    ICLOUD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    print(f"Dashboard written to {OUTPUT_FILE}")
    print("On iPhone: Files app -> iCloud Drive -> Administratif -> Banque et Finance ->")
    print("Finance Tracker -> dashboard.html -> open in Safari -> Share -> Add to Home Screen.")


if __name__ == "__main__":
    main()
