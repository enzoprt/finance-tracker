"""Shared HTML assembly for the dashboard, used by both the static iCloud
build (build_dashboard.py) and the local live server (serve_dashboard.py)
so the two never drift apart on how placeholders get filled in.
"""

from pathlib import Path

from src.config import PROJECT_ROOT

TEMPLATE_FILE = PROJECT_ROOT / "dashboard" / "template.html"
AI_OVERVIEW_FILE = PROJECT_ROOT / "dashboard" / "ai_overview.html"


def render_dashboard_html(summary_json_text: str) -> str:
    # Escape "</" so a stray "</script>" inside a transaction description
    # (however unlikely) can't break out of the inline <script> block.
    summary_json = summary_json_text.replace("</", "<\\/")
    ai_overview = AI_OVERVIEW_FILE.read_text(encoding="utf-8") if AI_OVERVIEW_FILE.is_file() else (
        "<p class=\"empty\">Not written yet - ask Claude to add an AI Overview.</p>"
    )

    html = TEMPLATE_FILE.read_text(encoding="utf-8")
    html = html.replace("__SUMMARY_JSON__", summary_json)
    html = html.replace("__AI_OVERVIEW__", ai_overview)
    return html
