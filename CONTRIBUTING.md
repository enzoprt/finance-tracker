# Contributing

Thanks for considering it. This started as a personal project, but it's
public and free (MIT-licensed) specifically so other people can use it and
make it better.

A few practical notes since this is maintained by one person in their spare
time, not a company:

- **Open an issue before a big PR.** For anything more than a small fix -
  new features, new bank support, a different UI approach - open an issue
  first to talk it through. Saves everyone the disappointment of a large PR
  that doesn't fit the direction of the project.
- **Bug reports and small fixes are always welcome as a direct PR.**
- **Response times vary.** This is a spare-time project - a review might
  take a few days.

## Before you start

- Read [`README.md`](README.md) for setup and how the pieces fit together.
- Read [`CLAUDE.md`](CLAUDE.md) if you're touching anything related to
  banks, the broker integration, or personalization - it documents exactly
  what's currently hardcoded to the original setup (LCL/N26/Saxo/France)
  and what genuinely needs to change to generalize it further. If you're
  adding support for a new bank, this is required reading first.

## What's especially welcome

- **Support for more banks.** Enable Banking covers a lot of European
  banks; only two are wired up today. See `CLAUDE.md` section 3 for
  exactly what needs to change (it's more than adding credentials).
- **Support for non-European banks/aggregators** (e.g. Plaid for North
  America) - a bigger lift, worth an issue first to discuss the approach.
- **More `SPENDING_KEYWORDS` entries** (`src/spending.py`) for merchants
  in other countries - the category/subcategory structure is meant to be
  broadly applicable, the keyword list just needs more real-world coverage.
- **Dashboard features** in the same spirit as what's there: computed
  from `data/summary.json`, no live API calls from the browser, no
  credentials ever reaching the frontend.

## Ground rules for any change

- **Never commit real credentials, tokens, or personal financial data.**
  `.env`, `*.pem`, and everything under `data/` are gitignored for a
  reason - don't work around that. If you're testing with your own real
  accounts, double-check `git status`/`git diff` before committing.
- **No live API calls from the dashboard.** The whole point of the
  architecture is that `dashboard/template.html` only ever reads a
  pre-computed `data/summary.json` embedded inline - keep it that way.
- **Match the existing code style.** Minimal comments (only for non-obvious
  *why*, never restating what the code already says), no speculative
  abstractions for hypothetical future needs, no unrequested refactors
  bundled into a feature PR.
- **Watch for keyword collisions** if you're touching `src/spending.py`'s
  classifier - short substrings can match inside unrelated words (real
  examples that shipped and got caught: `"MAXI"` matched inside the name
  "Maxime", `"BUT"` matched inside "début", `"APPLE "` matched inside
  "pineapple"). Grep real transaction descriptions plus a few adversarial
  strings before trusting a new short keyword.
- **Verify your change actually renders**, not just that it type-checks.
  There's no automated test suite yet - screenshot or otherwise visually
  confirm dashboard changes work (a fully synthetic `data/summary.json` is
  fine for this and is exactly how the README's screenshots were made -
  never use real financial data for testing artifacts you might share).

## Submitting a PR

1. Fork, branch, make your change.
2. Confirm nothing under `data/`, `.env`, or any real personal data is
   staged (`git status`, `git diff`).
3. Open the PR against `main` with a short description of what changed and
   why, and how you verified it.

## Reporting bugs / requesting features

Use the issue templates - they ask for just enough context (what you
expected, what happened, how to reproduce) to act on quickly.
