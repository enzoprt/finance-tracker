# Finance Tracker

Personal financial dashboard aggregating a Saxo Bank brokerage account (ETFs)
and two bank accounts (LCL, N26). Backend runs locally in Python and writes a
single `data/summary.json`; a static single-file dashboard reads that JSON
data embedded inline (no fetch, no live API calls, no credentials in the
browser) and is synced to iCloud Drive for use on iPhone.

## Setup

Requires Python 3.12 (not 3.14: `yfinance`'s `curl_cffi` dependency
segfaults on 3.14 as of this writing - see `brew install python@3.12`).

```bash
cd finance-tracker
/opt/homebrew/opt/python@3.12/libexec/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in real values, .env is gitignored
```

## Saxo OpenAPI login

```bash
python -m scripts.test_saxo_connection
```

Set `SAXO_ENVIRONMENT` in `.env` to `SIM` (paper trading, safe for testing)
or `LIVE` (real account). This opens the system browser for Saxo login,
catches the OAuth redirect on `http://localhost:8080/callback`, exchanges
the code for tokens (stored in `data/saxo_tokens_{sim,live}.json`,
gitignored), and prints the logged-in accounts. Subsequent runs
reuse/refresh the stored tokens automatically. First-time LIVE login may
require accepting a pending disclaimer on saxotrader.com directly (outside
this flow) before the OAuth authorize step will succeed.

## Enable Banking (LCL, N26) login

```bash
python -m scripts.test_enablebanking_link LCL
python -m scripts.test_enablebanking_link N26
```

Runs the PSD2 consent flow: opens the browser, catches the redirect on a
local HTTPS listener (self-signed cert - expect a one-time browser
warning), and stores the session in `data/enablebanking_session_{bank}.json`.
Only accounts explicitly linked via the Enable Banking control panel
("Link accounts") are returned by the API - link there first if a fresh
consent comes back with an empty `accounts` list.

Regulated savings accounts (Livret A, Livret Jeune, ...) are outside PSD2
scope and can never be fetched via any bank's API. Their balances are
tracked manually: seed values live in `data/livret_assignments.json`, and
the tool auto-detects internal transfers on the LCL current account
afterwards, prompting you to assign new ones to a livret by editing that
file.

## Building the data and the dashboard

```bash
python -m scripts.build_summary                     # last 12 months
python -m scripts.build_summary 2024-04-01 2026-07-15  # custom performance window
python -m scripts.build_dashboard
```

`build_summary` fetches everything once and writes `data/summary.json`
(net worth, ETF performance vs benchmark, fees, cash flow, FX cost,
anomalies, ETF geographic/sector allocation). It's resilient to Enable
Banking's PSD2 rate limits - if a fresh fetch gets a 429, it falls back to
the last cached data for that account rather than failing outright.

`build_dashboard` embeds that JSON into `dashboard/template.html` and
writes the result to iCloud Drive:
`Administratif/Banque et Finance/Finance Tracker/dashboard.html`. On
iPhone: Files app -> that path -> open in Safari -> Share -> Add to Home
Screen. Since the data is embedded (not fetched live), it works offline
and doesn't require being on the same network as the Mac.

Individual reports can also be built/inspected standalone via
`scripts/build_transactions.py`, `scripts/build_networth.py`, and
`scripts/build_performance.py`.

## Using the dashboard on the Mac, with a working Refresh button

```bash
python -m scripts.serve_dashboard
```

Serves the dashboard at `http://127.0.0.1:8787/`, bound strictly to
127.0.0.1 - never reachable from the phone or the network. Its Refresh
button re-runs `build_summary` + `build_dashboard` and reloads. The
iCloud-synced copy used on the phone has no server behind it, so tapping
Refresh there just explains that it only works via this local server on
the Mac.

### Dock launcher (recommended over running the command by hand)

```bash
bash scripts/install-macos-app.sh
```

Generates `~/Applications/Finance Tracker.app` - a real double-clickable
app (same "shell script wearing a .app bundle" trick as this user's other
project, Orca Profile Manager - no compiled binary, `Info.plist` just
points at a generated `launch.sh`). Clicking it starts
`scripts.serve_dashboard` in the background if it isn't already running,
then opens Safari straight to the dashboard - no terminal needed day to
day. Drag it from `~/Applications` onto the Dock once, then that's the
whole workflow going forward. The background server has no "quit" from
the app itself; it's harmless (127.0.0.1-only) but stays running until the
Mac restarts or you kill it by hand (`ps aux | grep serve_dashboard`).

## The "AI Overview" tab

`dashboard/ai_overview.en.html` / `dashboard/ai_overview.fr.html` are a
hand-written analysis (portfolio construction, fund overlap, performance
vs benchmark, tax-wrapper usage, opinions on what to consider changing),
one per language with an EN/FR toggle button on the tab itself - unlike
the rest of the dashboard, neither is computed by a script. Both get
embedded into the dashboard as-is by `build_dashboard.py` and
`serve_dashboard.py` (via `src/dashboard_render.py`). To refresh them
after a meaningful change (new funds, a big deposit, months of new
transaction history), ask a Claude Code session to re-read the latest
`data/summary.json` plus the real Saxo account structure and rewrite both
files - they won't update on their own.
