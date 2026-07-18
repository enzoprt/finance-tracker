## What changed and why

## How this was verified

<!-- No automated test suite yet - describe how you confirmed this works:
     ran it against real data, screenshotted a synthetic summary.json,
     manually walked through the affected tab/script, etc. -->

## Checklist

- [ ] No real credentials, tokens, or personal financial data in this diff
      (`git status` / `git diff` double-checked)
- [ ] If this touches `src/spending.py`: checked new short keywords against
      real transaction descriptions and a few adversarial strings for
      substring collisions
- [ ] If this is a new bank/broker: read `CLAUDE.md` first
