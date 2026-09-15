# U2 — Reproducible download of the funding-rate series

Date: 2026-09-14. Companion to `docs/01-data-audit.md` (U1 + U2 additions).

## 1. What this unit delivers

- `data/baseline/` — the nine JSONL files audited in U1, copied verbatim from the
  private working repo, plus `SHA256SUMS`. **Tracked in git**; this is the evidence a
  third party verifies a fresh download against. From here on the analysis reads from
  `data/baseline/`, never from the private repo.
- `scripts/download.py` — one command that re-downloads the nine series from the public
  APIs of Hyperliquid and Binance. No credentials, no third-party packages
  (Python ≥ 3.9 standard library only). Output goes to `data/downloaded/`, which is
  **git-ignored** (regenerable).
- `scripts/verify.py` — record-by-record comparison of `data/downloaded/` against
  `data/baseline/`. Results in §7.

```
python3 scripts/download.py          # all nine series → data/downloaded/
python3 scripts/verify.py            # comparison table on stdout
```

Options: `--only hl|binance`, `--hl-start`, `--binance-start`, `--end` (ISO-8601 UTC,
inclusive), `--out`. Defaults reproduce the baseline windows: Hyperliquid from
2025-09-10 04:00:00 UTC (the baseline's first record), Binance from the first record the
API has, both venues up to "now". The download therefore extends past the baseline's
last timestamp; the verification reports those extra records as such (§7).

## 2. Output format

One JSON object per line, serialised with Python's `json.dumps` default separators
(`", "` and `": "`), fields in the order the API returns them. This is exactly the
layout of the baseline files, so a re-download of an unchanged window can be
byte-identical; whether it is, is reported in §7.

```
{"coin": "BTC", "fundingRate": "0.0000125", "premium": "0.0001378486", "time": 1757476800083}
{"symbol": "BTCUSDT", "fundingTime": 1568102400000, "fundingRate": "0.00010000", "markPrice": "", "rateType": "Regular"}
```

Rates are kept as the decimal strings the APIs send; nothing is parsed to float.

Side files in `data/downloaded/`: `intervals.json` (the detected-interval report, §5)
and `manifest.json` (start/end parameters, record counts, first/last timestamp, wall
clock of the run).

## 3. Endpoints and pagination

### Hyperliquid

- `POST https://api.hyperliquid.xyz/info`, body
  `{"type": "fundingHistory", "coin": "<COIN>", "startTime": <ms>, "endTime": <ms>}`.
  Docs: <https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals>
  (consulted 2026-09-14).
- `startTime` is required and inclusive; `endTime` is optional, inclusive, defaults to
  now. Both verified empirically on 2026-09-14 (a request with `startTime` equal to a
  record's `time` returns that record; `+1 ms` excludes it).
- Response: ascending array of `{coin, fundingRate, premium, time}`. The docs do **not**
  state a page cap; empirically every call returns at most **500** records (three
  independent checks: `startTime=0`, `startTime=2025-09-10`, and a window ending in
  2027 all return exactly 500). The downloader treats 500 as the cap and stops on a
  short page.
- Paging: next call with `startTime = last.time + 1`. 8,760 records = 18 calls.
- `startTime = 0` works and returns the oldest retained history (2023-05-12 00:00 for
  BTC/ETH/SOL).
- No rate-limit headers are returned; the budget must be tracked client-side.

### Binance USDⓈ-M futures

- `GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=<SYM>&startTime=<ms>&endTime=<ms>&limit=1000`.
  Docs: <https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History>
  (consulted 2026-09-14).
- `limit` default 100, max 1,000. `startTime` and `endTime` are both inclusive (verified
  2026-09-14 the same way as above). Response ascending, fields
  `{symbol, fundingTime, fundingRate, markPrice, rateType}`; `rateType` is still
  returned by the live endpoint (U1 asked to verify this).
- **Pitfall:** `startTime = 0` is treated as *absent* and the endpoint returns the most
  recent records (documented: "returns most recent 200 records when start/end times
  omitted", observed: latest 3 with `limit=3`). "From the beginning" must be
  `startTime = 1`; the downloader does this by default.
- Paging: next call with `startTime = last.fundingTime + 1`. BTCUSDT's 7,673 records =
  8 calls.
- The response carries no `X-MBX-USED-WEIGHT-*` header for this endpoint (checked
  2026-09-14; it sits under a separate request-count limiter, see §4).

## 4. Rate limits and pacing

| Venue | Documented limit | What the downloader does |
|---|---|---|
| Hyperliquid | 1,200 weight/min per IP, shared by all REST calls. `fundingHistory` weighs 20 + 1 per 20 items returned (a full 500-row page = 45). Docs: <https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits> | Sliding 60 s window, budget 1,000 weight; sleeps before a call that would exceed it. ≈ 22 calls/min, so the five coins take ≈ 4–5 min. |
| Binance | `REQUEST_WEIGHT` 2,400/min per IP (from `exchangeInfo.rateLimits`), and `/fapi/v1/fundingRate` additionally shares a **500 requests per 5 min** limiter with `/fapi/v1/fundingInfo` (endpoint docs). | ≥ 0.7 s between calls (≤ 86/min). The four symbols need 26 calls in total. |

## 5. Interval detection

The settlement interval is never assumed. For each series the downloader computes the
delta between consecutive timestamps, rounds it to the nearest minute (this only absorbs
the sub-second settlement jitter, ≤ 261 ms on Hyperliquid and ≤ 47 ms on Binance), and
groups consecutive equal deltas into runs. Each run is reported with its interval, first
and last timestamp, number of deltas, and the raw min/max delta in ms so the jitter is
visible too. The report is printed at the end of the run and written to
`data/downloaded/intervals.json`. The table from the 2026-09-14 run follows.

Run of 2026-09-14 21:25–21:30 UTC (defaults, i.e. up to "now"):

| Series | Interval | From (UTC) | To (UTC) | Deltas | Raw delta min..max (ms) |
|---|---|---|---|---|---|
| funding-BTC.jsonl | 1 h | 2025-09-10 04:00 | 2026-09-14 21:00 | 8,873 | 3,599,779..3,600,229 |
| funding-ETH.jsonl | 1 h | 2025-09-10 04:00 | 2026-09-14 21:00 | 8,873 | 3,599,779..3,600,229 |
| funding-SOL.jsonl | 1 h | 2025-09-10 04:00 | 2026-09-14 21:00 | 8,873 | 3,599,779..3,600,229 |
| funding-HYPE.jsonl | 1 h | 2025-09-10 04:00 | 2026-09-14 21:00 | 8,873 | 3,599,779..3,600,229 |
| funding-PURR.jsonl | 1 h | 2025-09-10 04:00 | 2026-09-14 21:00 | 8,873 | 3,599,779..3,600,229 |
| binance-funding-BTCUSDT.jsonl | 8 h | 2019-09-10 08:00 | 2026-09-14 16:00 | 7,684 | 28,799,955..28,800,047 |
| binance-funding-ETHUSDT.jsonl | 8 h | 2019-11-27 08:00 | 2026-09-14 16:00 | 7,450 | 28,799,955..28,800,047 |
| binance-funding-SOLUSDT.jsonl | 8 h | 2020-09-13 16:00 | 2022-11-09 16:00 | 2,361 | 28,799,955..28,800,047 |
| binance-funding-SOLUSDT.jsonl | 4 h | 2022-11-09 16:00 | 2022-11-10 04:00 | 3 | 14,399,988..14,400,014 |
| binance-funding-SOLUSDT.jsonl | 2 h | 2022-11-10 04:00 | 2022-11-18 08:00 | 98 | 7,199,973..7,200,027 |
| binance-funding-SOLUSDT.jsonl | 8 h | 2022-11-18 08:00 | 2026-09-14 16:00 | 4,189 | 28,799,972..28,800,026 |
| binance-funding-HYPEUSDT.jsonl | 4 h | 2025-05-30 12:00 | 2026-06-24 00:00 | 2,337 | 14,399,976..14,400,021 |
| binance-funding-HYPEUSDT.jsonl | 8 h | 2026-06-24 00:00 | 2026-06-24 08:00 | 1 | 28,800,000..28,800,000 |
| binance-funding-HYPEUSDT.jsonl | 4 h | 2026-06-24 08:00 | 2026-09-14 20:00 | 495 | 14,399,982..14,400,026 |

This matches §9 of the audit exactly (same regime boundaries), with the runs extended
to the download time. The single 8 h delta in HYPEUSDT is the missing 2026-06-24 04:00
settlement, which the live API still does not return. No new cadence change appeared
between 2026-09-10 and 2026-09-14.

## 6. Retry policy

Implemented in `request_json()` of `scripts/download.py`:

| Condition | Action |
|---|---|
| HTTP 451 (Binance geographic block) | Abort immediately with exit code 3 and a message pointing to §8. Retrying cannot help. |
| HTTP 429 (rate limit) or 418 (Binance IP ban) | Sleep `Retry-After` seconds if the header is present, else exponential backoff; then retry. |
| HTTP 5xx, timeout (30 s), connection error | Exponential backoff 1, 2, 4, 8, 16, 16 s; at most 6 attempts, then abort. |
| Any other 4xx | Abort: the request itself is wrong. |

Every page is checked for monotonic timestamps against the rows already collected; a
non-monotonic page aborts the run rather than silently deduplicating.

The 2026-09-14 run from this laptop needed no retries on either venue.

## 7. Verification: downloaded vs. baseline

`python3 scripts/verify.py`, run 2026-09-14 right after the download. Key = exact
settlement timestamp in ms. "Identical" = same timestamp and every field byte-equal
(`coin`/`symbol`, `fundingRate`, `premium`/`markPrice`/`rateType`, timestamp).

| Series | Baseline | Downloaded | Identical | Differ in value | Only in baseline | Only in downloaded (before / inside / after baseline span) |
|---|---|---|---|---|---|---|
| funding-BTC.jsonl | 8,760 | 8,874 | 8,760 | 0 | 0 | 114 (0 / 0 / 114) |
| funding-ETH.jsonl | 8,760 | 8,874 | 8,760 | 0 | 0 | 114 (0 / 0 / 114) |
| funding-SOL.jsonl | 8,760 | 8,874 | 8,760 | 0 | 0 | 114 (0 / 0 / 114) |
| funding-HYPE.jsonl | 8,760 | 8,874 | 8,760 | 0 | 0 | 114 (0 / 0 / 114) |
| funding-PURR.jsonl | 8,760 | 8,874 | 8,760 | 0 | 0 | 114 (0 / 0 / 114) |
| binance-funding-BTCUSDT.jsonl | 7,673 | 7,685 | 7,673 | 0 | 0 | 12 (0 / 0 / 12) |
| binance-funding-ETHUSDT.jsonl | 7,439 | 7,451 | 7,439 | 0 | 0 | 12 (0 / 0 / 12) |
| binance-funding-SOLUSDT.jsonl | 6,640 | 6,652 | 6,640 | 0 | 0 | 12 (0 / 0 / 12) |
| binance-funding-HYPEUSDT.jsonl | 2,809 | 2,834 | 2,809 | 0 | 0 | 25 (0 / 0 / 25) |

Findings, stated as they are:

- Every record of the baseline is present in the download with identical timestamp and
  identical field values, in all nine series. Zero records differ in value; zero
  records are only in the baseline.
- The only records present in one side and absent in the other are the ones the API
  served **after** the baseline's last timestamp, because the default `--end` is "now":
  114 hourly settlements per Hyperliquid coin (2026-09-10 04:00 → 2026-09-14 21:00),
  12 eight-hourly settlements for BTCUSDT/ETHUSDT/SOLUSDT (2026-09-11 00:00 →
  2026-09-14 16:00) and 25 four-hourly ones for HYPEUSDT (2026-09-10 20:00 → 2026-09-14
  20:00). None falls before or inside the baseline span.
- Byte-level: the first N lines of each downloaded file (N = baseline record count)
  hash to exactly the baseline's SHA-256 in `data/baseline/SHA256SUMS`, for all nine
  files. The full downloaded files hash differently only because of the appended
  records. So the serialiser matches the one used for the baseline, and the venues
  returned the same bytes (including the ms jitter of every timestamp) five days later.
- The ms jitter in the timestamps is therefore a property of the venue's record, not of
  the download moment: it is stable across downloads.

Spans of this run (first .. last timestamp, UTC):

| Series | Baseline | Downloaded |
|---|---|---|
| funding-{BTC,ETH,SOL,HYPE,PURR} | 2025-09-10 04:00:00.083 .. 2026-09-10 03:00:00.048 | 2025-09-10 04:00:00.083 .. 2026-09-14 21:00:00.027 |
| binance-funding-BTCUSDT | 2019-09-10 08:00:00.000 .. 2026-09-10 16:00:00.002 | 2019-09-10 08:00:00.000 .. 2026-09-14 16:00:00.000 |
| binance-funding-ETHUSDT | 2019-11-27 08:00:00.000 .. 2026-09-10 16:00:00.002 | 2019-11-27 08:00:00.000 .. 2026-09-14 16:00:00.000 |
| binance-funding-SOLUSDT | 2020-09-13 16:00:00.004 .. 2026-09-10 16:00:00.002 | 2020-09-13 16:00:00.004 .. 2026-09-14 16:00:00.000 |
| binance-funding-HYPEUSDT | 2025-05-30 12:00:00.006 .. 2026-09-10 16:00:00.002 | 2025-05-30 12:00:00.006 .. 2026-09-14 20:00:00.008 |

SHA-256 of the full downloaded files of this run (informative; they will change with
every run because the window grows):

```
a69209f2291db4fc71a49ed1ba3ea2687134448a55973bfde5e35f3f0f3fa94b  funding-BTC.jsonl
ac37778a21ed4ca937e778c082e25eb71a3cb195247eca618166688a3e9ef3b9  funding-ETH.jsonl
ff6a255c2c5ef400fbc973f3987fc1264a0faa7a9487825b19fbbf5e068dfe31  funding-SOL.jsonl
bcce946f97de0ed8d9e9a288d0dbed95e664772be18827df7f0e8d080d4c7cc6  funding-HYPE.jsonl
696ba03b440dbfc51d2437432e24a39a8dbe5dff4b8af436db1f1d6ab2329302  funding-PURR.jsonl
3fb0bef28849843d19cdc70c4ff1b44484fd0dbc17379feb629fb60eed99f693  binance-funding-BTCUSDT.jsonl
506fd31b7dd93442c601304e8f638e42e470af8a570f4a367fe0d40db0cdf9bd  binance-funding-ETHUSDT.jsonl
7c0b9c809649a2ccb1528566411dd91c8eb5bc1edf454c551a3f2ac9420a5875  binance-funding-SOLUSDT.jsonl
cf0bc7ceaffd1e2ab37d06543a2769f836032eb81b84e403ad7c32f3c51e55f7  binance-funding-HYPEUSDT.jsonl
```

How a third party reproduces this check: run the two commands of §1 from a
non-restricted network (§8); expect the "Identical" column to equal the baseline count
and "Only in downloaded" to contain only records after the baseline span. Any record in
"Differ in value" or "Only in baseline" means the venue rewrote history and should be
reported, not patched.

## 8. Precondition for third parties: Binance geographic restriction

Binance Futures (`fapi.binance.com`) refuses requests from IP addresses it maps to a
"Restricted Location" under section *b. Eligibility* of its Terms of Use. This applies
to **public, unauthenticated market-data endpoints** such as `fundingRate` as well; it
is enforced by IP, not by account.

- **How it manifests.** HTTP status **451 Unavailable For Legal Reasons**, with a
  body saying that the service is unavailable from a restricted location and pointing
  to section b, Eligibility, of <https://www.binance.com/en/terms> (as described in the
  community reports below; not observed from this laptop, which is not blocked). The
  downloader prints the body it receives and exits with code 3 without retrying.
- **Where it fails.** Reported consistently from the United States (residential and
  cloud), and from cloud regions located there (e.g. AWS `us-east-1`, GCP `us-*`);
  Binance's terms name the United States, Malaysia and Ontario (Canada) among restricted
  locations, and the list can change. Reports:
  <https://dev.binance.vision/t/error-451-when-accessing-the-futures-api-from-us/16725>,
  <https://dev.binance.vision/t/google-cloud-and-ip-restriction-451-on-fapi-binance/13820>,
  <https://github.com/ccxt/ccxt/issues/15872>.
- **Where it works.** The 2026-09-14 run succeeded from this laptop on a residential
  connection in **Mexico** (the CloudFront edge that answered was `DFW`; the CDN edge
  location is not the client's location and is not what Binance checks).
  Community reports indicate EU (Ireland, Frankfurt) and APAC (Singapore, Tokyo) cloud
  regions work.
- **What to do if it occurs.** Run the downloader from a non-restricted network or
  region (`--only binance` re-runs just that venue). Do not proxy through a
  restricted-jurisdiction exit. The Hyperliquid half is unaffected: `--only hl` works
  from anywhere; Hyperliquid's API has no geographic block (verified from the same
  laptop, and none is documented).
- Not a geo-block: HTTP 403 from `fapi.binance.com` is a WAF/CDN rejection (typically
  missing or blocked `User-Agent`); the downloader sends a descriptive `User-Agent`.

