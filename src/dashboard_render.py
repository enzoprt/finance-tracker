"""Shared HTML assembly for the dashboard, used by both the static iCloud
build (build_dashboard.py) and the local live server (serve_dashboard.py)
so the two never drift apart on how placeholders get filled in.
"""

from pathlib import Path

from src.config import PROJECT_ROOT

TEMPLATE_FILE = PROJECT_ROOT / "dashboard" / "template.html"
AI_OVERVIEW_EN_FILE = PROJECT_ROOT / "dashboard" / "ai_overview.en.html"
AI_OVERVIEW_FR_FILE = PROJECT_ROOT / "dashboard" / "ai_overview.fr.html"

_MISSING_MESSAGE = "<p class=\"empty\">Not written yet - ask Claude to add an AI Overview.</p>"


def _read_or_placeholder(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else _MISSING_MESSAGE


def render_dashboard_html(summary_json_text: str) -> str:
    # Escape "</" so a stray "</script>" inside a transaction description
    # (however unlikely) can't break out of the inline <script> block.
    summary_json = summary_json_text.replace("</", "<\\/")

    html = TEMPLATE_FILE.read_text(encoding="utf-8")
    html = html.replace("__SUMMARY_JSON__", summary_json)
    html = html.replace("__AI_OVERVIEW_EN__", _read_or_placeholder(AI_OVERVIEW_EN_FILE))
    html = html.replace("__AI_OVERVIEW_FR__", _read_or_placeholder(AI_OVERVIEW_FR_FILE))
    return html
