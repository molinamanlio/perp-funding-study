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
