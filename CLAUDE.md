# Notes for Claude Code

This project was built end-to-end, over several sessions, for one specific
person: a French user with a Saxo Bank brokerage account and two French/
European bank accounts (LCL, N26), initially for everyday tracking plus a
4-month exchange semester in Quebec. Most of the *architecture* is generic
(local Python backend -> single `data/summary.json` -> static HTML
dashboard with no live API calls), but a real chunk of the *content* is
specific to that first user: their name, their bank pairing, their
merchant history, their tax situation.

If you're picking this project up **for a different person**, read this
whole file before touching anything. It's organized as a checklist: what
must change, what's already generic, and what a "new bank" actually
involves (it's more than one line).

## 1. Credentials and identity - `.env`

Copy `.env.example` to `.env` and fill in the new user's own values (never
copy someone else's `.env`, obviously). See `.env.example` for what each
variable is; two are worth calling out here:

- `ACCOUNT_HOLDER_SURNAME` - not just a label. `src/enablebanking/
  normalize.py`'s `_is_self_transfer()` uses it to detect transfers
  between the user's own accounts (e.g. towards a savings account), by
  checking whether a transfer-type transaction's remittance text contains
  this surname. Get it wrong and internal transfers silently get counted
  as real spending or income. That same function's
  `TRANSFER_PREFIXES = ("VIR", "VIREMENT")` is itself French SEPA
  transfer-label vocabulary - a non-French bank may label transfers
  differently in its transaction descriptions, which would make this
  detection miss entirely (not fail loudly - just silently not fire).
  Check a real transfer transaction from the new bank before trusting
  this still works.
- `ENABLE_BANKING_PRIVATE_KEY_PATH` - an absolute path to the `.pem` key
  downloaded at Enable Banking app registration. Put the new user's own
  key somewhere private (outside the repo; anywhere under `data/` works
  since that's gitignored) and point this at it - don't reuse the
  original user's key file or path.

## 2. Hardcoded to the original user - grep for these before shipping

- `dashboard/template.html` - the `.app-footer` div hardcodes **"Finance
  Tracker © 2026 Enzo Pierrot"** and embeds that user's own logo as a
  base64 PNG. Replace both with the new user's name and (optionally) a
  new logo - see the "App icon" section of `README.md` for how the
  original icon/footer were produced, as a template for redoing it.
- `scripts/build_dashboard.py` - `ICLOUD_DIR` is a hardcoded **French**
  iCloud Drive path (`Administratif/Banque et Finance/Finance Tracker`).
  Change it to wherever the new user wants their dashboard synced (or
  drop iCloud entirely and pick a different sync mechanism - nothing else
  depends on this specific path).
- `assets/icon.png` - the original user's logo. Fine to keep as a
  placeholder, but it's a specific design choice (blue square, white
  trend-line arrow) made for one person via a Gemini prompt - see
  `README.md`'s "App icon" section if the new user wants their own.
- `dashboard/ai_overview.en.html` / `ai_overview.fr.html` - **do not
  copy these forward at all.** They're gitignored (real personal
  financial data - net worth, holdings, tax situation, opinions on what
  to sell/buy) and won't exist in a fresh clone. For a new user, these
  need to be *written from scratch* by asking a Claude Code session to
  read the new user's real `data/summary.json` + live account structure
  and produce a fresh analysis - see `dashboard/ai_overview.example.html`
  for the placeholder that ships instead, and `README.md`'s "AI Overview"
  section for the expected structure (EN/FR toggle, disclaimer, portfolio
  construction, performance vs. benchmark, tax-wrapper usage, opinions).
- `data/livret_assignments.json` (gitignored, won't exist in a fresh
  clone anyway) - French-specific concept (Livret A, Livret Jeune, LDDS -
  regulated savings accounts outside PSD2 scope). If the new user isn't
  French, or has no such accounts, `src/livrets.py`'s whole reconciliation
  step is dead weight - either leave it (it degrades gracefully to "no
  livrets configured, nothing to reconcile") or strip it out if it's
  confusing to have unused.

## 3. Adding or swapping banks - this is NOT just editing a list

Enable Banking (the PSD2 aggregator this project uses) supports a wide
range of European banks. `scripts/list_aspsps_fr.py` lists **French**
ASPSPs specifically (it was written to find LCL/N26's exact names,
hardcodes `country="FR"` and filters for `"lcl"`/`"n26"` substrings) -
for a new user in a different country, edit its country filter before
it's useful again. **Non-European banks (US, Canadian, etc.) are very
likely NOT covered by Enable Banking at all** - PSD2/Open Banking is an
EU/UK regulatory framework. If the new user banks outside Europe, this
whole integration layer (`src/enablebanking/`) would need to be replaced
with a different aggregator (e.g. Plaid for North America) - a genuinely
new integration, not a config change. Don't attempt to force Enable
Banking to work with a non-European bank.

The consent/linking flow itself also defaults to France:
`src/enablebanking/auth.py`'s `link_account(aspsp_name, aspsp_country:
str = "FR", ...)` and its caller `scripts/test_enablebanking_link.py`
(`link_account(bank, aspsp_country="FR")`) - pass the new bank's real
country code if it isn't French. Consent also expires
(`CONSENT_VALIDITY_DAYS = 180` in `src/enablebanking/auth.py`) - expect
to re-run the linking flow periodically, not just once.

Assuming the new bank(s) *are* on Enable Banking, the current code is
**hardcoded to exactly two banks (LCL, N26) in more places than it looks
like** - swapping or adding one is a real code change, not just new
credentials. Concretely:

- **The fetch loop is duplicated in three places, not one** - `for bank,
  label in (("LCL", "LCL Compte Courant"), ("N26", "N26")):` appears
  near-identically in `scripts/build_summary.py`, `scripts/
  build_transactions.py`, and `scripts/build_networth.py` (the latter
  also calls `load_session("LCL")`/`load_session("N26")` by name
  directly). Update all three, not just `build_summary.py` - it's easy to
  fix the main pipeline and miss the standalone inspection scripts. The
  `label` string becomes the `account` field on every `Transaction` from
  that bank (shown throughout the dashboard, e.g. the Budget tab's
  transaction table) - pick something readable.
- **`src/networth.py`**'s `build_net_worth()` - the function signature
  itself takes named `lcl_balance`/`lcl_currency`/`n26_balance`/
  `n26_currency` parameters, and hardcodes the account keys `"LCL Compte
  Courant"`/`"N26"` inside its body. This is the part that's genuinely
  NOT generic yet: a third bank, or different banks entirely, don't fit
  this signature. You'll need to change it to accept a generic
  `dict[str, tuple[float, str]]` (or similar) of bank name -> (balance,
  currency), and update every call site accordingly (see previous bullet
  - `build_networth.py` calls it too). Don't just bolt on a third named
  parameter - genericize it properly since it'll keep needing to change
  otherwise.
- **`src/enablebanking/normalize.py`**'s `_is_fee()` and `_fee_type()` -
  these branch on `aspsp_name == "LCL"` with a **binary if/else that
  falls through to N26's rules for anything else**. This is a real
  landmine: a third bank added to the fetch loop without touching this
  file will silently get categorized using N26's English "Fee" keyword
  and fee-type rules, which will misclassify (or miss) that bank's actual
  fees if its transaction descriptions look different. Before adding a
  bank, look at a handful of its real transaction descriptions (fees
  especially - card fees, FX markup, overdraft interest) and either add a
  new keyword tuple for it (converting the if/else into a dict keyed by
  `aspsp_name`, e.g. `BANK_FEE_KEYWORDS = {"LCL": (...), "N26": (...),
  "NewBank": (...)}`) or confirm its vocabulary genuinely matches an
  existing bank's before reusing those rules. Also note `src/fees.py`'s
  docstring assumption that "all fees detected so far are EUR-denominated
  (LCL and N26 both report in EUR)" - a bank reporting in another
  currency would need that assumption revisited too.
- **`src/fx_cost.py`**'s foreign-currency detection - the regex
  (`FOREIGN_AMOUNT_PATTERN`) that extracts a foreign amount from a
  transaction description was validated against real LCL card purchases
  (format: `"XXX 99,99"`, ISO currency code + comma-decimal amount next
  to the merchant line). It's untested against N26's actual wording and
  will be untested against any new bank too - re-validate against a
  handful of real foreign-currency transactions from the new bank(s)
  before trusting the FX-markup numbers it produces. If the format
  differs, extend the regex/parsing rather than assuming it just works.
- **`src/spending.py`**'s `SPENDING_KEYWORDS` - the category/subcategory
  classifier, 174 entries total. Roughly ~64 are France-specific (EDF,
  Engie, Veolia, Orange/SFR/Bouygues/Free Mobile, Carrefour, Monoprix,
  Auchan, Biocoop, SNCF, RATP, Escota, Mutuelle, Pharmacie, Préfecture,
  Notaire, Impôts...), ~28 are Quebec/Canada-specific (Hydro-Québec,
  Vidéotron, Bell Canada, Fido, Rogers, IGA, Provigo, SuperC, Maxi, Tim
  Hortons, Jean Coutu, Shoppers, Air Canada, STM, SAQ, Petro-Canada,
  Cineplex, Opus/Exo...) added for one user's specific exchange trip, and
  ~4 are leftover residue from a single April 2026 Denmark trip
  (Rejsekort, Netto, Føtex, 7-Eleven) - none of that ~96 is going to be
  useful to a new user. The remaining ~78 are generic/international
  brands (Amazon, Netflix, Spotify, Uber, Airbnb, McDonald's, IKEA,
  PayPal, Steam, H&M, Zara, hotels, taxis...) and are worth keeping.
  None of it is hardcoded to a *bank* (it matches merchant names in
  transaction descriptions, regardless of which bank the transaction came
  through) - but a new user in a different country will see a LOT of
  "other" until their own recurring merchants get added here. Extend it
  incrementally as real "other"-bucket transactions show up (see the
  Budget tab's category breakdown) rather than trying to guess a new
  country's merchants upfront. Watch for substring collisions when adding
  short keywords (documented inline where it bit before: `"MAXI"` matched
  inside a common first name in a transfer description, `"BUT"` matched
  inside "début", `"APPLE "` matched inside "pineapple" - anchor
  short/generic keywords with leading AND trailing spaces, and grep real
  transaction descriptions plus a handful of adversarial strings before
  trusting a new short keyword).
  `MERCHANT_LABELS` (the display-name cleanup dict used by the
  Subscriptions card) is generic/international and needs no changes.
- **`src/model.py`**'s `Transaction.account` docstring comment
  (`# e.g. "LCL Compte Courant", "N26", "Saxo"`) - just a comment, purely
  cosmetic, but update it so it doesn't mislead the next person.
- **UI copy in `dashboard/template.html` names LCL/N26 directly** in
  several info-panel strings (e.g. the Fees card: `"Detected via keyword
  matching: COTISATION / FRAIS / AGIOS / COMMISSION for LCL, "Fee" for
  N26..."`, plus a few others referencing "LCL, N26" or "LCL/N26" by
  name). These are just explanatory text, not logic, but they'll actively
  mislead a new user if left as-is once the underlying banks change -
  grep `template.html` for "LCL" and "N26" and update each one to
  describe whatever banks are actually wired up.

## 4. Saxo Bank - genuinely broker-specific, not just configured

Unlike the bank layer, Saxo isn't a "swap the credentials" situation -
`src/saxo/` calls Saxo's own OpenAPI directly (positions, balances, trade
history, performance timeseries) and the whole Performance/Allocation/
"ETF fees" tab machinery is built against Saxo's specific response
shapes. If the new user uses a different broker entirely, that's a real
rewrite of `src/saxo/*.py` (and everywhere `SaxoClient` is imported), not
a config change - out of scope for a quick personalization pass. If the
new user *also* uses Saxo, only `.env`'s `SAXO_APP_KEY`/`SAXO_APP_SECRET`
(from developer.saxo, one app registration per person) need to change,
plus a fresh SIM or LIVE login (`python -m scripts.test_saxo_connection`).

One Saxo-specific assumption worth knowing about: ETF position values use
`MarketValueOpenInBaseCurrency` (cost basis at trade-open), not live
market value, because this app's Saxo entitlements don't include a live
market-data subscription. If the new user's Saxo app *does* have one,
`src/saxo/instruments.py`'s `fetch_etf_holdings()` could be upgraded to
use live prices - not done here, documented as a known simplification.

## 5. Already generic - shouldn't need changes

- The whole dashboard chart/interaction layer (`renderMultiLineChart`,
  tooltips, min/max axis labels, the range pickers, the Budget tab's
  custom-date mode, the iOS-style switches) - built against
  `SUMMARY.transactions`/`SUMMARY.performance`/etc. generically, no
  hardcoded account names or currencies beyond EUR display formatting.
- The category/subcategory *taxonomy structure* itself (housing,
  transport, groceries, dining, health, subscriptions, education, gifts,
  admin/taxes, ...) - designed to be broadly applicable to anyone's
  adult-life spending, not just the original user's. Only the *keyword
  list* underneath it needs new-user-specific extension (see §3 above).
- `src/etf_fees.py`'s TER lookup (works for any UCITS ETF via yfinance,
  not tied to specific fund choices) - though its
  `FRENCH_CTO_FLAT_TAX_RATE` (30%) and the post-tax-value assumption
  (everything in a taxable CTO, PEA/PEA-PME empty) are France-specific
  tax law. A non-French user's tax situation is different - either adapt
  the rate/logic to their actual tax wrapper and rules, or drop the
  post-tax figures (both in the Performance tab's "ETF fees" card and the
  Overview tab's "After tax on gains" stat) if they don't apply. Don't
  ship a French tax assumption silently for someone it doesn't apply to.
- `scripts/install-macos-app.sh` (the Dock launcher generator) - resolves
  its own path at runtime (`PROJECT_DIR="$(cd "$(dirname
  "${BASH_SOURCE[0]}")/.." && pwd)"`), nothing to edit; just re-run it on
  the new machine.

## 6. General approach for a personalization pass

1. Fresh `.env` with the new user's real credentials (§1).
2. Grep for the original user's name/paths (§2) and replace/remove.
3. Figure out the new user's actual bank(s), check Enable Banking
   coverage, and do the real code work in §3 - don't just add credentials
   and assume it works, verify against real transaction descriptions from
   THAT bank.
4. Run the pipeline (`build_summary` -> `build_dashboard`) against real
   data, then look at the "other" bucket in the Budget tab's category
   breakdown and extend `SPENDING_KEYWORDS` for real recurring merchants
   that show up.
5. Write a fresh `ai_overview.en.html`/`.fr.html` (or just one language,
   if the new user doesn't need bilingual) once there's enough real
   history to say something useful.
6. Decide whether the France-specific tax assumptions (§5, `src/
   etf_fees.py`) apply, and adapt or remove them.
7. Re-run `scripts/install-macos-app.sh` for the Dock launcher, on
   whatever Mac the new user actually uses.

Don't assume any of this from a stale memory of a previous session - the
codebase is the source of truth. If something described here has since
changed, trust the code and update this file.
