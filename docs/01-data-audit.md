# U1 — Audit of the existing funding-rate data

Date of audit: 2026-09-13. Everything below was computed in this session directly from
the files; nothing is copied from earlier notes. Numbers from the original working notes
are quoted only in the "Discrepancies" section, and only to compare.

## 1. Where the data actually is

The task brief said the series live under `evidencia/` in the private working repo.
They do not. `evidencia/` (156 KB, 12 files) holds only manifests, checksums, journals
and a reconciliation note for the *order-book capture* of 2026-09-03..09-10; the
~90 MB of book snapshots themselves are git-ignored and are **not present** on this
machine (only their SHA-256 sums are).

The funding-rate histories that this study is about are in the git-ignored directory
`data/historico/` of the private repo: nine JSONL files, 7.1 MB in total, downloaded
2026-09-09 (Hyperliquid) and 2026-09-10 (Binance). No download script survives in the
repo; the files were pulled ad hoc. U2 has to build the downloader from scratch and
prove it reproduces these files.

A 420-line fixture (`fixtures/purr-funding-bursts-2026-09-06.jsonl`, 7 h of 1-minute
snapshots) also exists, but it is a private-runtime snapshot format, not a funding
history, and is out of scope for the public study.

## 2. Inventory

Timestamps are UTC. "Grid" is the settlement cadence the series is expected to follow;
"coverage" is the share of grid slots between first and last record that have a record.

| Source | File | Market | First record | Last record | Grid | Records | Grid slots present | Coverage |
|---|---|---|---|---|---|---|---|---|
| Hyperliquid `fundingHistory` | `funding-BTC.jsonl` | BTC perp | 2025-09-10 04:00 | 2026-09-10 03:00 | 1 h | 8,760 | 8,760 / 8,760 | 100.00 % |
| Hyperliquid `fundingHistory` | `funding-ETH.jsonl` | ETH perp | 2025-09-10 04:00 | 2026-09-10 03:00 | 1 h | 8,760 | 8,760 / 8,760 | 100.00 % |
| Hyperliquid `fundingHistory` | `funding-SOL.jsonl` | SOL perp | 2025-09-10 04:00 | 2026-09-10 03:00 | 1 h | 8,760 | 8,760 / 8,760 | 100.00 % |
| Hyperliquid `fundingHistory` | `funding-HYPE.jsonl` | HYPE perp | 2025-09-10 04:00 | 2026-09-10 03:00 | 1 h | 8,760 | 8,760 / 8,760 | 100.00 % |
| Hyperliquid `fundingHistory` | `funding-PURR.jsonl` | PURR perp | 2025-09-10 04:00 | 2026-09-10 03:00 | 1 h | 8,760 | 8,760 / 8,760 | 100.00 % |
| Binance USDⓈ-M `fapi/v1/fundingRate` | `binance-funding-BTCUSDT.jsonl` | BTCUSDT perp | 2019-09-10 08:00 | 2026-09-10 16:00 | 8 h | 7,673 | 7,673 / 7,673 | 100.00 % |
| Binance USDⓈ-M `fapi/v1/fundingRate` | `binance-funding-ETHUSDT.jsonl` | ETHUSDT perp | 2019-11-27 08:00 | 2026-09-10 16:00 | 8 h | 7,439 | 7,439 / 7,439 | 100.00 % |
| Binance USDⓈ-M `fapi/v1/fundingRate` | `binance-funding-SOLUSDT.jsonl` | SOLUSDT perp | 2020-09-13 16:00 | 2026-09-10 16:00 | 8 h (+ 75 off-grid, see §4) | 6,640 | 6,565 / 6,565 | 100.00 % |
| Binance USDⓈ-M `fapi/v1/fundingRate` | `binance-funding-HYPEUSDT.jsonl` | HYPEUSDT perp | 2025-05-30 12:00 | 2026-09-10 16:00 | 4 h | 2,809 | 2,809 / 2,810 | 99.96 % |

Totals: Hyperliquid 43,800 records (5 × 8,760); Binance 24,561 records.

All nine files: every line parses as JSON, timestamps strictly increasing, no duplicate
timestamps, no duplicate grid slots, a single symbol per file.

### SHA-256 of the audited files (reference set for the U2 comparison)

```
941eece3a78160a0aadac592a0ea54aa58c8ae4c4d8f35949f386c91d747d7d3  funding-BTC.jsonl
4e8b97d1be012f5f6262505ae3caf8d87fad8a1df636d24a15a8e9e3aef4033b  funding-ETH.jsonl
8afc309ab82d0f2887434f5938140c2cc09a9f786d5ce9b28131a142d7d4fea3  funding-HYPE.jsonl
cca8065264368201507e8fbb087742c72827de23c11bd35d7a353690bef12b56  funding-PURR.jsonl
cde4fcb463e22c14d9e718eee965d8085dcb221654db4b10f7691c1617d486f0  funding-SOL.jsonl
bd297ae775ff3b8dbd5c441438cf607c6efffab45c50c0005560da3123161dba  binance-funding-BTCUSDT.jsonl
5aedc10a16e9acc9abb1e646437fae2b0c5c1755e8f4f4374719e408a98672a8  binance-funding-ETHUSDT.jsonl
265c777051bfb901d42a8684301fa135d826be66a4d6098ec363474296d56069  binance-funding-HYPEUSDT.jsonl
98c1d2d0075aded5741c1842b072307e9238af1f5c2672791d6e072eaeefd57b  binance-funding-SOLUSDT.jsonl
```

Byte-identical reproduction in U2 is *not* expected (field order, whitespace and float
formatting depend on the serializer); the comparison must be on parsed `(time, rate)`
pairs.

## 3. Schema

**Hyperliquid** (one record per settlement, exactly the `fundingHistory` response shape):

```json
{"coin": "BTC", "fundingRate": "0.0000125", "premium": "0.0001378486", "time": 1757476800083}
```

- `fundingRate`: decimal string, rate per settlement (hourly). The venue default
  `0.0000125`/h (= 0.01 %/8 h, ≈ 10.95 % APR) is the mode: BTC 4,363 h, ETH 4,665 h,
  SOL 3,151 h, HYPE 6,382 h, PURR 7,199 h out of 8,760.
- `premium`: decimal string, the mark-vs-oracle premium used by the venue's formula.
  Kept but unused so far.
- `time`: settlement time, ms since epoch, jittered by ≤ 261 ms after the top of the hour.

**Binance** (one record per settlement, the `fapi/v1/fundingRate` response shape):

```json
{"symbol": "BTCUSDT", "fundingTime": 1568102400000, "fundingRate": "0.00010000", "markPrice": "", "rateType": "Regular"}
```

- `fundingRate`: decimal string, rate per settlement (8 h, or 4 h for HYPEUSDT).
  The Binance default `0.0001`/8 h is the mode for BTC (2,711), ETH (2,572), SOL (2,297);
  HYPEUSDT's mode is `0.00005`/4 h (1,683 of 2,809).
- `fundingTime`: ms since epoch, jitter ≤ 47 ms.
- `markPrice`: empty string for every record before 2023-10-31 08:00 (BTC 4,536, ETH
  4,302, SOL 3,503 empty), populated afterwards. Not needed for this study.
- `rateType`: `"Regular"` in all 24,561 records. The field is in the stored data; whether
  the live endpoint still returns it is to be verified in U2.

## 4. Gaps and irregularities

1. **HYPEUSDT (Binance) has one missing 4 h slot**: 2026-06-24 04:00 UTC. The record at
   00:00 is followed directly by 08:00. This is the only gap in the whole dataset. The
   earlier note "cero huecos" was stated for Hyperliquid only and is correct there.
2. **SOLUSDT (Binance) has 75 extra records off the 8 h grid**, 2022-11-09 20:00 to
   2022-11-18 06:00: the cadence went 8 h → 4 h (from 2022-11-09 16:00) → 2 h
   (2022-11-10 04:00 to 2022-11-18 08:00) → back to 8 h. This coincides with the FTX
   collapse; Binance shortens the settlement interval when a symbol's rate is capped.
   Every 8 h grid slot in that window is still present, so this is *not* a gap, but any
   annualisation must use the actual interval between settlements, not a constant 8 h.
   Within that window, 40 SOLUSDT records sit at |rate| ≥ 0.003 and the minimum is
   −0.02 (the −2 % cap), which matters for per-year statistics on 2022.
3. **Binance cadence differs by symbol**: 8 h for BTC/ETH/SOL, 4 h for HYPEUSDT
   throughout. Annualisation factors: 1,095/yr for 8 h, 2,190/yr for 4 h, 8,760/yr for
   Hyperliquid's 1 h. Comparisons across venues must be done on annualised rates, or
   by aggregating Hyperliquid's hourly rates into the Binance 8 h windows.
4. **Series ends are not aligned**: Hyperliquid stops at 2026-09-10 03:00, Binance at
   2026-09-10 16:00. The last 13 h of Binance have no Hyperliquid counterpart. The
   overlap window is 2025-09-10 04:00 → 2026-09-10 03:00 for BTC/ETH/SOL/HYPE; PURR has
   no Binance counterpart (no PURRUSDT perp there).
5. **Hyperliquid window is not a calendar year**: it is exactly 8,760 hourly settlements
   ending at the download time, i.e. 2025-09-10 04:00 → 2026-09-10 03:00. "2025" and
   "2026" statistics on Hyperliquid therefore cover ~3.7 and ~8.3 months respectively,
   not full years. Calendar-year tables in the earlier notes mix full Binance years with
   these partial Hyperliquid years.
6. **`markPrice` is empty before 2023-10-31** on Binance. Irrelevant to the rate
   analysis but must not be parsed as a number.

Value-range sanity check (per-settlement rates): Hyperliquid BTC −0.0000694…0.0002327,
ETH −0.0003856…0.0000834, SOL −0.0020514…0.0000975, HYPE −0.0018662…0.0001810,
PURR −0.0038914…0.0015906. Binance BTC ±0.003 (cap hit twice), ETH −0.003563…0.00375,
SOL −0.02…0.003325, HYPE −0.000651…0.001977. Nothing looks like a parsing artefact.

## 5. Discrepancies against the recalled figures

Only claims that can be checked from an inventory are checked here; the substantive
claims (share of hours above base, regime shift, venue comparison) are recomputed in U3.

| Recalled | Audit result |
|---|---|
| "One year of Hyperliquid funding history in five markets" | Confirmed: 5 markets × 8,760 hourly records, 100 % coverage. |
| "Binance history since 2019" | Partly: BTCUSDT from 2019-09-10, ETHUSDT from 2019-11-27, SOLUSDT only from 2020-09-13, HYPEUSDT from 2025-05-30. "Since 2019" holds for BTC and ETH only. |
| "Data is in `evidencia/`" | No. It is in the git-ignored `data/historico/`. `evidencia/` holds only manifests and checksums of the book capture, whose payload is absent on this machine. |
| "Zero gaps" (from the working notes, Hyperliquid) | Confirmed for Hyperliquid. Binance HYPEUSDT has one missing 4 h slot (2026-06-24 04:00). |
| Working notes: "Intervalo 8 h (HYPE 4 h)" | Correct as the base cadence, but SOLUSDT ran at 4 h and 2 h for nine days in Nov 2022 (75 extra records). Any code that assumes a constant interval per symbol is wrong for that window. |

## 6. Consequences for U2 and U3

- U2 must reproduce **both** endpoints without credentials and compare on parsed
  `(time, rate)` pairs against the hashes above. Expect the live Hyperliquid response to
  extend past 2026-09-10 03:00 and Binance past 16:00; the comparison is on the
  intersection of timestamps. Hyperliquid `fundingHistory` is documented to return at
  most 500 records per call, so pagination by `startTime` is required for 8,760 rows;
  Binance `fundingRate` returns up to 1,000 per call and also needs `startTime` paging.
  Binance blocks some server IP ranges (HTTP 451); this is a reproducibility caveat to
  document, not something to work around.
- U3 must annualise using the observed interval between consecutive settlements, treat
  the Hyperliquid 2025/2026 calendar years as partial, and state that "since 2019" is
  BTC/ETH only.

---

# U2 additions to the audit (2026-09-14)

Added in U2. Everything here was queried live on 2026-09-14 from this laptop, or
computed from the frozen copies in `data/baseline/` (same hashes as §2).

## 7. Hyperliquid base ("interest rate") component

Source: Hyperliquid docs, *Trading → Funding*,
<https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding>, consulted
2026-09-14. The page's GitBook metadata says "Last updated 2026-04-08T03:25Z".

Verbatim statements from that page:

- "For consistency with CEXs, interest rate component is predetermined at 0.01% every
  8 hours, which is 0.00125% every hour, or 11.6% APR paid to short."
- "The funding rate on Hyperliquid is paid every hour."
- "The funding rate formula applies to 8 hour funding rate. However, funding is paid
  every hour at one eighth of the computed rate for each hour."
- "Funding Rate (F) = Average Premium Index (P) + clamp (interest rate - Premium
  Index (P), -0.0005, 0.0005)."
- "The premium is sampled every 5 seconds and averaged over the hour."
- "Funding on Hyperliquid is capped at 4%/hour."
- HIP-3 perps use a different premium formula and a deployer-set interest rate. The
  five markets in this study (BTC, ETH, SOL, HYPE, PURR) are canonical perps listed in
  the `meta` universe, not HIP-3 markets, so the standard 0.01 %/8 h applies.

**Value and unit.** Interest rate = 0.0001 per 8 h = 0.0000125 per hour (decimal
fraction, i.e. 0.01 %/8 h = 0.00125 %/h). Annualised two ways (both recomputed in
session on 2026-09-14):

- Simple: hourly rate × 8,760 = 0.0000125 × 8,760 = 0.1095 = 10.95 %/yr.
- Compound: (1 + rate per 8 h)^1095 − 1 = (1 + 0.0001)^1095 − 1 = 0.115714 =
  11.57 %/yr, with 1,095 = 3 settlements/day × 365 days.

The docs' "11.6 % APR" is the compound figure (11.57 % rounded to one decimal).
Both are valid conventions for expressing the same value; the documentation is not in
error, it simply uses the compound convention while the simple one gives 10.95 %.

**How it enters the stored `fundingRate`.** The stored value is the hourly rate
F/8. When |P| is inside the clamp band, `interest − P` is not clamped and F = P + (r − P)
= r, so the hourly value is exactly r/8 = 0.0000125 regardless of the premium. The
value only departs from 0.0000125 when the premium moves outside the band, i.e.
F = P − 0.0005 (P > r + 0.0005) or F = P + 0.0005 (P < r − 0.0005). That is why
`0.0000125` is the modal value in every series (§3), and that is the "base" against
which U3 counts hours above/below base.

**Did the base change between 2025-09-10 and 2026-09-10?** No evidence that it did:

- The docs page was edited on 2026-04-08 (GitBook metadata). The archived text before
  that edit could not be retrieved from this machine (web.archive.org is not reachable
  from this session), so the *text* diff is unknown. The likely addition is the HIP-3
  premium paragraph, which post-dates the HIP-3 launch; this is an inference.
- The *data* is unambiguous: the exact string `0.0000125` is the modal `fundingRate` in
  every calendar month of the window for all five coins (counts of records exactly at
  base / records in month):

  | Coin | 2025-09 | 10 | 11 | 12 | 2026-01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | BTC | 423/500 | 552/744 | 530/720 | 357/744 | 452/744 | 185/672 | 159/744 | 88/720 | 200/744 | 270/720 | 572/744 | 419/744 | 156/220 |
  | ETH | 320/500 | 514/744 | 463/720 | 456/744 | 520/744 | 176/672 | 178/744 | 90/720 | 415/744 | 283/720 | 597/744 | 444/744 | 209/220 |
  | SOL | 305/500 | 395/744 | 159/720 | 360/744 | 378/744 | 14/672 | 40/744 | 149/720 | 279/744 | 190/720 | 372/744 | 405/744 | 105/220 |
  | HYPE | 269/500 | 473/744 | 521/720 | 665/744 | 630/744 | 496/672 | 568/744 | 421/720 | 544/744 | 552/720 | 577/744 | 506/744 | 160/220 |
  | PURR | 379/500 | 574/744 | 569/720 | 676/744 | 551/744 | 526/672 | 656/744 | 638/720 | 569/744 | 582/720 | 667/744 | 630/744 | 182/220 |

  A change of the interest rate would move that plateau to a different constant; no
  other constant appears more than twice in any series. U3 can use r = 0.0000125/h for
  the whole window.

**Annualisation convention for U3.** U3 annualises with the **simple** convention:
per-settlement rate × number of settlements per year, where the number of settlements
is derived from the observed interval between consecutive timestamps (8,760 for 1 h,
2,190 for 4 h, 1,095 for 8 h, 4,380 for 2 h during the SOLUSDT episode). Under this
convention the Hyperliquid base is 10.95 %/yr. The convention must be applied
**identically to the observed funding and to the base rate**: comparing observed rates
annualised one way against a base annualised the other way (e.g. observed simple vs.
base 11.57 % compound) shifts the threshold and biases the count of hours above the
base. Whenever a compound figure is quoted for readability, both sides are recomputed
under that convention together.

## 8. Listing dates vs. series start

### Hyperliquid

The `meta` info request carries no listing date. The exchange's own earliest evidence
is the first record returned by `fundingHistory` with `startTime = 0` (queried
2026-09-14):

| Coin | Earliest record in the API (UTC) | Series start in baseline | Records available before series start |
|---|---|---|---|
| BTC | 2023-05-12 00:00:00.048 | 2025-09-10 04:00 | ≈ 2 y 4 m |
| ETH | 2023-05-12 00:00:00.048 | 2025-09-10 04:00 | ≈ 2 y 4 m |
| SOL | 2023-05-12 00:00:00.048 | 2025-09-10 04:00 | ≈ 2 y 4 m |
| HYPE | 2024-12-05 10:00:00.004 | 2025-09-10 04:00 | ≈ 9 m |
| PURR | 2024-11-04 10:00:00.074 | 2025-09-10 04:00 | ≈ 10 m |

- BTC, ETH and SOL all start at the same millisecond, 2023-05-12 00:00. Hyperliquid's
  perp exchange was live before that date, so this is the start of the API's retained
  history, not a listing date (inference; the docs do not state a retention policy).
- HYPE's first funding record (2024-12-05 10:00) is six days after the HYPE token
  genesis (2024-11-29). PURR's first record is 2024-11-04 10:00. Both are taken as the
  perp listing time as far as the exchange reports it.
- The baseline series start (2025-09-10 04:00) is a **download-window choice**: exactly
  8,760 hourly records back from the download time. It is not a listing boundary for any
  of the five coins. The "100 % coverage" of §2 therefore means "no hole inside the
  chosen window", and there is a block of older data before the window on all five.

### Binance

`GET /fapi/v1/exchangeInfo` exposes `onboardDate` per symbol; the earliest funding
record was obtained with `startTime = 1` (note: `startTime = 0` is treated as absent by
Binance and returns the *latest* records — see `docs/02-download.md`).

| Symbol | `onboardDate` (UTC) | Earliest `fundingRate` record in API | Series start in baseline | Difference |
|---|---|---|---|---|
| BTCUSDT | 2019-09-08 17:55:00 | 2019-09-10 08:00:00 | 2019-09-10 08:00 | First record is 38 h 05 min **after** onboarding. The four 8 h slots 2019-09-09 00:00, 08:00, 16:00 and 2019-09-10 00:00 are absent from the API itself. |
| ETHUSDT | 2019-11-27 07:45:00 | 2019-11-27 08:00:00 | 2019-11-27 08:00 | First grid slot after onboarding (15 min). Consistent. |
| SOLUSDT | 2020-09-14 07:00:00 | 2020-09-13 16:00:00.004 | 2020-09-13 16:00 | First record is 15 h **before** `onboardDate`; two records (2020-09-13 16:00, 2020-09-14 00:00) precede it. Reported as is; the semantics of `onboardDate` are not documented. |
| HYPEUSDT | 2025-05-30 10:30:00 | 2025-05-30 12:00:00.006 | 2025-05-30 12:00 | First 4 h slot after the announced launch time (10:30 UTC, per the listing announcement). Consistent. |

In all four cases the baseline series starts at the exchange's earliest available
record, so no block is missing at the start *relative to what the API serves*. For
BTCUSDT the exchange's own history begins 38 h after the contract was onboarded.

Sources: `exchangeInfo` and `fundingRate` queried 2026-09-14; HYPEUSDT launch
announcement "Binance Futures Will Launch USDⓈ-Margined HYPEUSDT Perpetual Contract"
(2025-05-30), <https://www.binance.com/en/support/announcement/detail/9166fe6f7b8a4b438262df3a040b007b>.

## 9. Binance funding-interval history per market

Derived from the baseline files: delta between consecutive `fundingTime`, rounded to
the nearest hour (jitter ≤ 47 ms), grouped into runs.

| Symbol | Interval | From (UTC) | To (UTC) | Deltas |
|---|---|---|---|---|
| BTCUSDT | 8 h | 2019-09-10 08:00 | 2026-09-10 16:00 | 7,672 (entire series) |
| ETHUSDT | 8 h | 2019-11-27 08:00 | 2026-09-10 16:00 | 7,438 (entire series) |
| SOLUSDT | 8 h | 2020-09-13 16:00 | 2022-11-09 16:00 | 2,361 |
| SOLUSDT | 4 h | 2022-11-09 16:00 | 2022-11-10 04:00 | 3 |
| SOLUSDT | 2 h | 2022-11-10 04:00 | 2022-11-18 08:00 | 98 |
| SOLUSDT | 8 h | 2022-11-18 08:00 | 2026-09-10 16:00 | 4,177 |
| HYPEUSDT | 4 h | 2025-05-30 12:00 | 2026-06-24 00:00 | 2,337 |
| HYPEUSDT | 8 h | 2026-06-24 00:00 | 2026-06-24 08:00 | 1 (the missing slot of §4.1, not a cadence change) |
| HYPEUSDT | 4 h | 2026-06-24 08:00 | 2026-09-10 16:00 | 470 |

So the SOLUSDT episode of November 2022 is the **only** cadence change in the four
series; BTCUSDT and ETHUSDT have run at 8 h without interruption, and HYPEUSDT at 4 h
since listing. The one 8 h delta in HYPEUSDT is a single missing 4 h settlement
(2026-06-24 04:00); no Binance announcement explaining it was found.

Exchange-side documentation of the episodes:

- SOLUSDT, 2022-11-09: "Updates on Funding Rate Settlement Frequency and Capped Funding
  Rate Multiplier of SOLUSDT, SOLBUSD and SOLUSD Perpetual Futures Contracts",
  effective 2022-11-09 20:00 UTC, settlement every 4 h, cap ±2.00 %, multiplier 0.75 →
  1. It states: "there may be further adjustments to the funding rate settlement
  frequency of the aforementioned perpetual futures contracts. There will be no further
  announcement on such adjustments." The move to 2 h on 2022-11-10 04:00 and back to 8 h
  on 2022-11-18 08:00 were indeed not announced; they are known only from the data.
  <https://www.binance.com/en/support/announcement/updates-on-funding-rate-settlement-frequency-and-capped-funding-rate-multiplier-of-solusdt-solbusd-and-solusd-perpetual-futures-contracts-2022-11-09-e8be17e1e544418490e86723d84759f0>
- HYPEUSDT: listed 2025-05-30 10:30 UTC with "Funding Rate Settlement: Every Four
  Hours", cap ±2.00 % (announcement linked in §8).
- General rule since 2026-01-02 12:00 UTC: contracts on 1 h settlement revert to 4 h
  after 16 consecutive cycles with |rate| ≤ 0.025 %. No 1 h regime appears in the four
  series, so this rule has not affected them.
  <https://www.binance.com/en/support/announcement/detail/e4445d0389ce4defa6009021fcf6ee46>
- Current settings from `GET /fapi/v1/fundingInfo` (2026-09-14): BTCUSDT 8 h, cap
  ±0.300 %; ETHUSDT 8 h, cap ±0.300 %; SOLUSDT 8 h, cap ±0.375 %; HYPEUSDT 4 h, cap
  ±2.000 % (`updateTime` 2025-05-30 10:32 UTC). This endpoint reports only the
  *current* interval; it has no history, which is why the interval must be derived from
  timestamps (done by the U2 downloader).
