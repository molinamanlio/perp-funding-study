# U3 — Analysis of the funding-rate series

Generated 2026-09-14T23:38:57+00:00 by `scripts/analyse.py` from `data/full/`. Every number in this document and in the figures is computed by that script; none is typed by hand. Re-running the script regenerates this file, `docs/04-discrepancies.md`, `figures/` and `results/analysis.json`.

## 0. Dataset: `data/full/`

Downloaded with the U2 downloader, full retained history on both venues, frozen and hashed (`data/full/SHA256SUMS`):

```
python3 scripts/download.py --out data/full --hl-start 2023-01-01T00:00:00Z --end 2026-09-14T00:00:00Z
```

Binance is downloaded from its first record (`startTime=1`, the default). The Hyperliquid API returns from the start of its retained history regardless of the earlier `--hl-start`. The explicit `--end` makes the freeze reproducible (a re-run with the same arguments must hash identically unless a venue rewrites history). `data/baseline/` (U1) is untouched.

| Series | Records | First (UTC) | Last (UTC) | Hours covered | Days | Calendar years |
|---|---|---|---|---|---|---|
| Hyperliquid BTC | 28,734 | 2023-05-12 00:00 | 2026-09-13 23:00 | 29,308 | 1,221.2 | 2023, 2024, 2025, 2026 |
| Hyperliquid ETH | 28,734 | 2023-05-12 00:00 | 2026-09-13 23:00 | 29,308 | 1,221.2 | 2023, 2024, 2025, 2026 |
| Hyperliquid SOL | 28,734 | 2023-05-12 00:00 | 2026-09-13 23:00 | 29,308 | 1,221.2 | 2023, 2024, 2025, 2026 |
| Hyperliquid HYPE | 15,542 | 2024-12-05 10:00 | 2026-09-13 23:00 | 15,542 | 647.6 | 2024, 2025, 2026 |
| Hyperliquid PURR | 16,286 | 2024-11-04 10:00 | 2026-09-13 23:00 | 16,286 | 678.6 | 2024, 2025, 2026 |
| Binance BTCUSDT | 7,683 | 2019-09-10 08:00 | 2026-09-14 00:00 | 61,464 | 2,561.0 | 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026 |
| Binance ETHUSDT | 7,449 | 2019-11-27 08:00 | 2026-09-14 00:00 | 59,592 | 2,483.0 | 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026 |
| Binance SOLUSDT | 6,650 | 2020-09-13 16:00 | 2026-09-14 00:00 | 52,600 | 2,191.7 | 2020, 2021, 2022, 2023, 2024, 2025, 2026 |
| Binance HYPEUSDT | 2,829 | 2025-05-30 12:00 | 2026-09-14 00:00 | 11,316 | 471.5 | 2025, 2026 |

### 0.1 Comparison against `data/baseline/`

`python3 scripts/verify.py --downloaded data/full --json results/verify-full-vs-baseline.json` (same key and equality definition as docs/02-download.md §7):

| Series | Baseline | data/full | Identical | Differ in value | Only in baseline | Only in data/full (before / inside / after baseline span) |
|---|---|---|---|---|---|---|
| funding-BTC.jsonl | 8,760 | 28,734 | 8,760 | 0 | 0 | 19,974 (19,882 / 0 / 92) |
| funding-ETH.jsonl | 8,760 | 28,734 | 8,760 | 0 | 0 | 19,974 (19,882 / 0 / 92) |
| funding-SOL.jsonl | 8,760 | 28,734 | 8,760 | 0 | 0 | 19,974 (19,882 / 0 / 92) |
| funding-HYPE.jsonl | 8,760 | 15,542 | 8,760 | 0 | 0 | 6,782 (6,690 / 0 / 92) |
| funding-PURR.jsonl | 8,760 | 16,286 | 8,760 | 0 | 0 | 7,526 (7,434 / 0 / 92) |
| binance-funding-BTCUSDT.jsonl | 7,673 | 7,683 | 7,673 | 0 | 0 | 10 (0 / 0 / 10) |
| binance-funding-ETHUSDT.jsonl | 7,439 | 7,449 | 7,439 | 0 | 0 | 10 (0 / 0 / 10) |
| binance-funding-SOLUSDT.jsonl | 6,640 | 6,650 | 6,640 | 0 | 0 | 10 (0 / 0 / 10) |
| binance-funding-HYPEUSDT.jsonl | 2,809 | 2,829 | 2,809 | 0 | 0 | 20 (0 / 0 / 20) |

Result: 68,361 of 68,361 baseline records reappear identical in `data/full/`; 0 differ in value, 0 are only in the baseline, 0 are only in `data/full/` inside the baseline span. The extended dataset is a strict superset of the baseline; the analysis proceeds.

### 0.2 Settlement cadence observed in `data/full/` and how each run is treated

| Series | Delta | From (UTC) | To (UTC) | Deltas | Treatment |
|---|---|---|---|---|---|
| BTC (HL) | 8 h | 2023-05-12 00:00 | 2023-06-08 00:00 | 81 | cadence run |
| BTC (HL) | 1 h | 2023-06-08 00:00 | 2023-07-02 19:00 | 595 | cadence run |
| BTC (HL) | 2 h | 2023-07-02 19:00 | 2023-07-02 21:00 | 1 | omitted settlement(s); record annualised at 1 h |
| BTC (HL) | 1 h | 2023-07-02 21:00 | 2023-08-23 19:00 | 1,246 | cadence run |
| BTC (HL) | 2 h | 2023-08-23 19:00 | 2023-08-23 21:00 | 1 | omitted settlement(s); record annualised at 1 h |
| BTC (HL) | 1 h | 2023-08-23 21:00 | 2024-08-15 12:00 | 8,583 | cadence run |
| BTC (HL) | 2 h | 2024-08-15 12:00 | 2024-08-15 14:00 | 1 | omitted settlement(s); record annualised at 1 h |
| BTC (HL) | 1 h | 2024-08-15 14:00 | 2026-09-13 23:00 | 18,225 | cadence run |
| ETH (HL) | 8 h | 2023-05-12 00:00 | 2023-06-08 00:00 | 81 | cadence run |
| ETH (HL) | 1 h | 2023-06-08 00:00 | 2023-07-02 19:00 | 595 | cadence run |
| ETH (HL) | 2 h | 2023-07-02 19:00 | 2023-07-02 21:00 | 1 | omitted settlement(s); record annualised at 1 h |
| ETH (HL) | 1 h | 2023-07-02 21:00 | 2023-08-23 19:00 | 1,246 | cadence run |
| ETH (HL) | 2 h | 2023-08-23 19:00 | 2023-08-23 21:00 | 1 | omitted settlement(s); record annualised at 1 h |
| ETH (HL) | 1 h | 2023-08-23 21:00 | 2024-08-15 12:00 | 8,583 | cadence run |
| ETH (HL) | 2 h | 2024-08-15 12:00 | 2024-08-15 14:00 | 1 | omitted settlement(s); record annualised at 1 h |
| ETH (HL) | 1 h | 2024-08-15 14:00 | 2026-09-13 23:00 | 18,225 | cadence run |
| SOL (HL) | 8 h | 2023-05-12 00:00 | 2023-06-08 00:00 | 81 | cadence run |
| SOL (HL) | 1 h | 2023-06-08 00:00 | 2023-07-02 19:00 | 595 | cadence run |
| SOL (HL) | 2 h | 2023-07-02 19:00 | 2023-07-02 21:00 | 1 | omitted settlement(s); record annualised at 1 h |
| SOL (HL) | 1 h | 2023-07-02 21:00 | 2023-08-23 19:00 | 1,246 | cadence run |
| SOL (HL) | 2 h | 2023-08-23 19:00 | 2023-08-23 21:00 | 1 | omitted settlement(s); record annualised at 1 h |
| SOL (HL) | 1 h | 2023-08-23 21:00 | 2024-08-15 12:00 | 8,583 | cadence run |
| SOL (HL) | 2 h | 2024-08-15 12:00 | 2024-08-15 14:00 | 1 | omitted settlement(s); record annualised at 1 h |
| SOL (HL) | 1 h | 2024-08-15 14:00 | 2026-09-13 23:00 | 18,225 | cadence run |
| HYPE (HL) | 1 h | 2024-12-05 10:00 | 2026-09-13 23:00 | 15,541 | cadence run |
| PURR (HL) | 1 h | 2024-11-04 10:00 | 2026-09-13 23:00 | 16,285 | cadence run |
| BTCUSDT (Binance) | 8 h | 2019-09-10 08:00 | 2026-09-14 00:00 | 7,682 | cadence run |
| ETHUSDT (Binance) | 8 h | 2019-11-27 08:00 | 2026-09-14 00:00 | 7,448 | cadence run |
| SOLUSDT (Binance) | 8 h | 2020-09-13 16:00 | 2022-11-09 16:00 | 2,361 | cadence run |
| SOLUSDT (Binance) | 4 h | 2022-11-09 16:00 | 2022-11-10 04:00 | 3 | cadence run |
| SOLUSDT (Binance) | 2 h | 2022-11-10 04:00 | 2022-11-18 08:00 | 98 | cadence run |
| SOLUSDT (Binance) | 8 h | 2022-11-18 08:00 | 2026-09-14 00:00 | 4,187 | cadence run |
| HYPEUSDT (Binance) | 4 h | 2025-05-30 12:00 | 2026-06-24 00:00 | 2,337 | cadence run |
| HYPEUSDT (Binance) | 8 h | 2026-06-24 00:00 | 2026-06-24 08:00 | 1 | omitted settlement(s); record annualised at 4 h |
| HYPEUSDT (Binance) | 4 h | 2026-06-24 08:00 | 2026-09-14 00:00 | 490 | cadence run |

Omitted settlements (a single delta that is a whole multiple of the cadence on both sides of it): BTC (HL) 2023-07-02 20:00, BTC (HL) 2023-08-23 20:00, BTC (HL) 2024-08-15 13:00, ETH (HL) 2023-07-02 20:00, ETH (HL) 2023-08-23 20:00, ETH (HL) 2024-08-15 13:00, SOL (HL) 2023-07-02 20:00, SOL (HL) 2023-08-23 20:00, SOL (HL) 2024-08-15 13:00, HYPEUSDT (Binance) 2026-06-24 04:00.

Settlements executed minutes late (the next settlement then fell on the regular hour, so the two deltas sum to the cadence; both are rounded to the cadence). Each event affects every market listed, i.e. it is venue-wide: 2023-05-23 08:23:53 UTC, 503.9 min after the previous settlement (BTC, ETH, SOL); 2023-09-27 23:01:51 UTC, 61.9 min after the previous settlement (BTC, ETH, SOL); 2023-12-17 22:04:10 UTC, 64.2 min after the previous settlement (BTC, ETH, SOL); 2025-07-19 10:14:47 UTC, 74.8 min after the previous settlement (BTC, ETH, SOL, HYPE, PURR); 2025-07-27 12:01:50 UTC, 61.8 min after the previous settlement (BTC, ETH, SOL, HYPE, PURR).

## 1. Calculation rules

1. **Annualisation** is the simple convention fixed in docs/01-data-audit.md §7: per-settlement rate ×
   (8,760 h / interval in hours). It is applied identically to the observed funding and to the base rate.
   The Hyperliquid base component is 0.0000125 per hour, i.e. **10.95 %/yr** under this
   convention (the compound figure would be 11.57 %/yr; it is not used anywhere below).
   Binance's interest-rate component is 0.0001 per 8 h, the same value per hour, so one base line serves both venues.
2. **Settlements per year** are derived from the observed interval between consecutive timestamps, rounded to
   the nearest hour, never assumed: 8,760/yr for 1 h, 4,380/yr for 2 h, 2,190/yr for 4 h, 1,095/yr for 8 h. The
   SOLUSDT runs of November 2022 at 4 h and 2 h are annualised with their real interval, and so is
   Hyperliquid's own 8 h regime of May–June 2023 (§0.2), which the extended download revealed.
3. **Omitted settlements.** A single delta that is a whole multiple of the cadence on both sides of it is a missing
   settlement, not a cadence change. The record that follows it keeps the cadence of its run for annualisation
   and for the hour weight; the omitted slot is simply absent from every count (no imputation). This covers
   HYPEUSDT 2026-06-24 04:00 on Binance and the Hyperliquid slots listed in §0.2. For HYPEUSDT the 08:00 rate
   (0.00005000) is annualised as a 4 h rate; whether it accrued 4 h or 8 h is unknown. Under the
   alternative (annualise it as an 8 h rate) the HYPEUSDT full-history mean moves from
   8.5299 %/yr to 8.5268 %/yr, and that one
   record is classified "at" base as a 4 h rate versus
   "below" base as an 8 h rate: one settlement of
   2,829.
4. **Delayed settlements** (a settlement minutes late, the next one back on the hour) are rounded to the cadence;
   they are listed in §0.2. Apart from those, the largest departure of a timestamp from its rounded hour is
   25.3 s on Hyperliquid and 0.047 s on Binance; rounding to the hour is therefore
   unambiguous.
5. **Base classification** is an exact decimal comparison of the API string against the base per settlement
   (0.0000125 × interval hours), with no rounding and no float. Above/at/below counts are reported
   both as settlements and as hour-weighted shares (a settlement counts for its interval in hours).
6. **Partial calendar years** are marked with an asterisk and the number of days covered in every table and
   figure. A year is partial when the series does not span it (first settlement later than its interval after
   1 January 00:00 UTC, or last settlement earlier than its interval before 31 December 24:00 UTC). Years are
   assigned by the settlement timestamp in UTC.
7. **Means** are hour-weighted (each settlement weighted by its interval); on a pure 1 h grid this equals the
   plain mean. Medians and quantiles are per settlement, unweighted.
8. **Venue comparison** sums the Hyperliquid hourly rates falling in each Binance settlement window
   (t − I, t] and annualises both sides with I; windows not fully covered on the Hyperliquid side are dropped.
9. **No hand-typed numbers.** This file, docs/04, the figures and `results/analysis.json` are produced by
   `scripts/analyse.py` from `data/full/` only.

## 2. Main result: the funding distribution is a point mass at the base with two tails

Mechanically, F = P + clamp(r − P, −0.0005, 0.0005) equals r exactly whenever |r − P| ≤ 0.0005, so every hour whose average premium lies within ±0.05 % of the base settles at exactly 0.0000125/h. Shares of settlement-hours exactly at / strictly above / strictly below the base, per market and calendar year (Hyperliquid, exact decimal comparison, hour-weighted; * partial year with days covered):

| Market | Year | Settlements | Exactly at base | Above | Below | Settlements at / above / below |
|---|---|---|---|---|---|---|
| BTC | 2023* (234 d) | 5,047 | 30.2 % | 32.1 % | 37.7 % | 1,578 / 1,806 / 1,663 |
| BTC | 2024 | 8,783 | 55.3 % | 37.3 % | 7.3 % | 4,860 / 3,279 / 644 |
| BTC | 2025 | 8,760 | 66.1 % | 10.2 % | 23.7 % | 5,789 / 893 / 2,078 |
| BTC | 2026* (256 d) | 6,144 | 41.3 % | 0.7 % | 58.0 % | 2,535 / 44 / 3,565 |
| ETH | 2023* (234 d) | 5,047 | 33.8 % | 37.6 % | 28.6 % | 1,668 / 2,072 / 1,307 |
| ETH | 2024 | 8,783 | 51.1 % | 36.3 % | 12.7 % | 4,484 / 3,186 / 1,113 |
| ETH | 2025 | 8,760 | 55.9 % | 9.3 % | 34.7 % | 4,898 / 818 / 3,044 |
| ETH | 2026* (256 d) | 6,144 | 48.2 % | 0.2 % | 51.6 % | 2,960 / 11 / 3,173 |
| SOL | 2023* (234 d) | 5,047 | 20.8 % | 29.9 % | 49.3 % | 1,126 / 1,680 / 2,241 |
| SOL | 2024 | 8,783 | 48.3 % | 41.1 % | 10.6 % | 4,244 / 3,611 / 928 |
| SOL | 2025 | 8,760 | 51.7 % | 8.1 % | 40.1 % | 4,533 / 712 / 3,515 |
| SOL | 2026* (256 d) | 6,144 | 31.7 % | 0.7 % | 67.7 % | 1,945 / 40 / 4,159 |
| HYPE | 2024* (27 d) | 638 | 15.5 % | 83.9 % | 0.6 % | 99 / 535 / 4 |
| HYPE | 2025 | 8,760 | 64.5 % | 28.4 % | 7.1 % | 5,654 / 2,486 / 620 |
| HYPE | 2026* (256 d) | 6,144 | 73.1 % | 4.8 % | 22.1 % | 4,493 / 294 / 1,357 |
| PURR | 2024* (58 d) | 1,382 | 30.9 % | 67.6 % | 1.5 % | 427 / 934 / 21 |
| PURR | 2025 | 8,760 | 80.1 % | 18.7 % | 1.2 % | 7,014 / 1,637 / 109 |
| PURR | 2026* (256 d) | 6,144 | 82.4 % | 14.6 % | 3.0 % | 5,063 / 894 / 187 |

Whole retained history per market:

| Market | Span (UTC) | Settlements | Exactly at base | Above | Below |
|---|---|---|---|---|---|
| BTC | 2023-05-12 00:00 → 2026-09-13 23:00 | 28,734 | 50.8 % | 20.5 % | 28.7 % |
| ETH | 2023-05-12 00:00 → 2026-09-13 23:00 | 28,734 | 48.6 % | 20.9 % | 30.5 % |
| SOL | 2023-05-12 00:00 → 2026-09-13 23:00 | 28,734 | 40.6 % | 20.6 % | 38.8 % |
| HYPE | 2024-12-05 10:00 → 2026-09-13 23:00 | 15,542 | 65.9 % | 21.3 % | 12.7 % |
| PURR | 2024-11-04 10:00 → 2026-09-13 23:00 | 16,286 | 76.8 % | 21.3 % | 1.9 % |

![Base mass](../figures/fig0-base-mass.png)

*Figure 0 — top: hour-weighted share at / above / below the base per market-year; bottom: histogram of the annualised hourly rate per market (2 pp bins, log scale), grey bar = the bin containing the base.*

### 2.1 Invariance of the classification to the annualisation convention

Counts of settlements above / at / below the base over the whole history, computed four ways: exact decimal strings; float per-settlement rates; float simple-annualised rates vs. the simple-annualised base; float compound-annualised rates vs. the compound-annualised base. Since annualising is a strictly increasing transformation applied to both sides, the ordering cannot change; the table verifies it holds numerically too:

| Series | Records | Exact decimal | Float raw | Simple annualised | Compound annualised | Identical |
|---|---|---|---|---|---|---|
| Hyperliquid BTC | 28,734 | 6,022 / 14,762 / 7,950 | 6,022 / 14,762 / 7,950 | 6,022 / 14,762 / 7,950 | 6,022 / 14,762 / 7,950 | yes |
| Hyperliquid ETH | 28,734 | 6,087 / 14,010 / 8,637 | 6,087 / 14,010 / 8,637 | 6,087 / 14,010 / 8,637 | 6,087 / 14,010 / 8,637 | yes |
| Hyperliquid SOL | 28,734 | 6,043 / 11,848 / 10,843 | 6,043 / 11,848 / 10,843 | 6,043 / 11,848 / 10,843 | 6,043 / 11,848 / 10,843 | yes |
| Hyperliquid HYPE | 15,542 | 3,315 / 10,246 / 1,981 | 3,315 / 10,246 / 1,981 | 3,315 / 10,246 / 1,981 | 3,315 / 10,246 / 1,981 | yes |
| Hyperliquid PURR | 16,286 | 3,465 / 12,504 / 317 | 3,465 / 12,504 / 317 | 3,465 / 12,504 / 317 | 3,465 / 12,504 / 317 | yes |
| Binance BTCUSDT | 7,683 | 1,069 / 2,711 / 3,903 | 1,069 / 2,711 / 3,903 | 1,069 / 2,711 / 3,903 | 1,069 / 2,711 / 3,903 | yes |
| Binance ETHUSDT | 7,449 | 1,226 / 2,572 / 3,651 | 1,226 / 2,572 / 3,651 | 1,226 / 2,572 / 3,651 | 1,226 / 2,572 / 3,651 | yes |
| Binance SOLUSDT | 6,650 | 835 / 2,304 / 3,511 | 835 / 2,304 / 3,511 | 835 / 2,304 / 3,511 | 835 / 2,304 / 3,511 | yes |
| Binance HYPEUSDT | 2,829 | 228 / 1,690 / 911 | 228 / 1,690 / 911 | 228 / 1,690 / 911 | 228 / 1,690 / 911 | yes |

All four counts coincide for every series: the classification is invariant to the annualisation convention.

## 3. Annualised funding over time, with the base rate

![Time series](../figures/fig1-timeseries-annualised.png)

*Figure 1 — simple-annualised Hyperliquid funding, hour-weighted trailing means over 30 days (thick) and 7 days (thin); dashed line = base 10.95 %/yr.*

Per calendar year, %/yr (hour-weighted mean; per-settlement median and quantiles):

| Market | Year | Mean | Median | p5 | p25 | p75 | p95 | Min | Max |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2023* (234 d) | 13.53 | 10.95 | -19.2 | 1.92 | 25.76 | 68.2 | -145 | 397 |
| BTC | 2024 | 24.14 | 10.95 | 4.0 | 10.95 | 27.61 | 84.9 | -80 | 524 |
| BTC | 2025 | 10.63 | 10.95 | -5.4 | 10.95 | 10.95 | 26.8 | -80 | 297 |
| BTC | 2026* (256 d) | 4.73 | 7.77 | -11.2 | 0.44 | 10.95 | 10.9 | -61 | 49 |
| ETH | 2023* (234 d) | 20.09 | 10.95 | -10.1 | 10.17 | 35.63 | 83.7 | -274 | 443 |
| ETH | 2024 | 22.05 | 10.95 | -5.8 | 10.95 | 29.38 | 76.3 | -103 | 207 |
| ETH | 2025 | 8.53 | 10.95 | -11.0 | 5.38 | 10.95 | 24.8 | -338 | 136 |
| ETH | 2026* (256 d) | 5.44 | 10.44 | -11.6 | 2.02 | 10.95 | 10.9 | -64 | 73 |
| SOL | 2023* (234 d) | 11.71 | 10.95 | -54.7 | -15.81 | 30.54 | 116.9 | -181 | 341 |
| SOL | 2024 | 28.14 | 10.95 | -7.4 | 10.95 | 36.59 | 108.3 | -137 | 338 |
| SOL | 2025 | 5.31 | 10.95 | -21.6 | 0.92 | 10.95 | 23.2 | -1797 | 121 |
| SOL | 2026* (256 d) | -0.67 | 3.61 | -27.8 | -7.50 | 10.95 | 10.9 | -121 | 85 |
| HYPE | 2024* (27 d) | 118.79 | 93.85 | 10.9 | 33.67 | 176.56 | 323.9 | -437 | 723 |
| HYPE | 2025 | 22.07 | 10.95 | 3.7 | 10.95 | 16.85 | 83.6 | -1635 | 776 |
| HYPE | 2026* (256 d) | 9.05 | 10.95 | -9.6 | 10.95 | 10.95 | 10.9 | -88 | 159 |
| PURR | 2024* (58 d) | 151.74 | 83.07 | 10.9 | 10.95 | 225.69 | 519.5 | -325 | 1940 |
| PURR | 2025 | 27.94 | 10.95 | 10.9 | 10.95 | 10.95 | 139.6 | -3409 | 1393 |
| PURR | 2026* (256 d) | 25.66 | 10.95 | 10.9 | 10.95 | 10.95 | 158.3 | -1733 | 1363 |

## 4. Share of hours per year above the base

![Share above base](../figures/fig2-share-above-base.png)

*Figure 2 — hour-weighted share of each calendar year in which funding was strictly above the venue base (Hyperliquid left, Binance right, same base per hour on both).*

| Year | HL BTC | HL ETH | HL SOL | HL HYPE | HL PURR | BN BTCUSDT | BN ETHUSDT | BN SOLUSDT | BN HYPEUSDT |
|---|---|---|---|---|---|---|---|---|---|
| 2019 | — | — | — | — | — | 6.8 %* | 0.0 %* | — | — |
| 2020 | — | — | — | — | — | 26.8 % | 37.4 % | 9.8 %* | — |
| 2021 | — | — | — | — | — | 42.9 % | 45.4 % | 41.5 % | — |
| 2022 | — | — | — | — | — | 0.0 % | 0.0 % | 0.0 % | — |
| 2023 | 32.1 %* | 37.6 %* | 29.9 %* | — | — | 6.3 % | 6.9 % | 8.9 % | — |
| 2024 | 37.3 % | 36.3 % | 41.1 % | 83.9 %* | 67.6 %* | 19.4 % | 22.0 % | 22.7 % | — |
| 2025 | 10.2 % | 9.3 % | 8.1 % | 28.4 % | 18.7 % | 0.0 % | 0.0 % | 0.2 % | 16.3 %* |
| 2026 | 0.7 %* | 0.2 %* | 0.7 %* | 4.8 %* | 14.6 %* | 0.0 %* | 0.0 %* | 0.0 %* | 1.1 %* |

\* partial years: BTC 2023: 234 d (2023-05-12 00:00 → 2023-12-31 23:00); BTC 2026: 256 d (2026-01-01 00:00 → 2026-09-13 23:00); ETH 2023: 234 d (2023-05-12 00:00 → 2023-12-31 23:00); ETH 2026: 256 d (2026-01-01 00:00 → 2026-09-13 23:00); SOL 2023: 234 d (2023-05-12 00:00 → 2023-12-31 23:00); SOL 2026: 256 d (2026-01-01 00:00 → 2026-09-13 23:00); HYPE 2024: 27 d (2024-12-05 10:00 → 2024-12-31 23:00); HYPE 2026: 256 d (2026-01-01 00:00 → 2026-09-13 23:00); PURR 2024: 58 d (2024-11-04 10:00 → 2024-12-31 23:00); PURR 2026: 256 d (2026-01-01 00:00 → 2026-09-13 23:00); BTCUSDT 2019: 113 d (2019-09-10 08:00 → 2019-12-31 16:00); BTCUSDT 2026: 256 d (2026-01-01 00:00 → 2026-09-14 00:00); ETHUSDT 2019: 35 d (2019-11-27 08:00 → 2019-12-31 16:00); ETHUSDT 2026: 256 d (2026-01-01 00:00 → 2026-09-14 00:00); SOLUSDT 2020: 109 d (2020-09-13 16:00 → 2020-12-31 16:00); SOLUSDT 2026: 256 d (2026-01-01 00:00 → 2026-09-14 00:00); HYPEUSDT 2025: 216 d (2025-05-30 12:00 → 2025-12-31 20:00); HYPEUSDT 2026: 256 d (2026-01-01 00:00 → 2026-09-14 00:00).

Binance per year, for reference (same layout as §2, plus mean and median in %/yr):

| Symbol | Year | Settlements | Exactly at base | Above | Below | Mean | Median |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 2019* (113 d) | 338 | 66.9 % | 6.8 % | 26.3 % | 7.48 | 10.95 |
| BTCUSDT | 2020 | 1,098 | 50.5 % | 26.8 % | 22.8 % | 17.19 | 10.95 |
| BTCUSDT | 2021 | 1,095 | 43.1 % | 42.9 % | 14.0 % | 30.61 | 10.95 |
| BTCUSDT | 2022 | 1,095 | 30.8 % | 0.0 % | 69.2 % | 4.16 | 5.62 |
| BTCUSDT | 2023 | 1,095 | 38.5 % | 6.3 % | 55.2 % | 7.87 | 9.05 |
| BTCUSDT | 2024 | 1,098 | 42.1 % | 19.4 % | 38.5 % | 11.92 | 10.95 |
| BTCUSDT | 2025 | 1,095 | 17.2 % | 0.0 % | 82.8 % | 5.13 | 5.28 |
| BTCUSDT | 2026* (256 d) | 769 | 6.5 % | 0.0 % | 93.5 % | 2.79 | 3.37 |
| ETHUSDT | 2019* (35 d) | 104 | 78.8 % | 0.0 % | 21.2 % | 8.91 | 10.95 |
| ETHUSDT | 2020 | 1,098 | 56.8 % | 37.4 % | 5.7 % | 27.41 | 10.95 |
| ETHUSDT | 2021 | 1,095 | 44.8 % | 45.4 % | 9.8 % | 37.54 | 10.95 |
| ETHUSDT | 2022 | 1,095 | 25.8 % | 0.0 % | 74.2 % | 0.79 | 4.24 |
| ETHUSDT | 2023 | 1,095 | 37.3 % | 6.9 % | 55.8 % | 8.26 | 9.04 |
| ETHUSDT | 2024 | 1,098 | 39.6 % | 22.0 % | 38.3 % | 12.96 | 10.95 |
| ETHUSDT | 2025 | 1,095 | 19.4 % | 0.0 % | 80.6 % | 4.93 | 5.26 |
| ETHUSDT | 2026* (256 d) | 769 | 4.9 % | 0.0 % | 95.1 % | 1.70 | 2.58 |
| SOLUSDT | 2020* (109 d) | 328 | 62.8 % | 9.8 % | 27.4 % | -12.52 | 10.95 |
| SOLUSDT | 2021 | 1,095 | 52.1 % | 41.5 % | 6.5 % | 28.59 | 10.95 |
| SOLUSDT | 2022 | 1,170 | 33.4 % | 0.0 % | 66.6 % | -38.00 | 1.43 |
| SOLUSDT | 2023 | 1,095 | 41.2 % | 8.9 % | 49.9 % | 1.30 | 10.95 |
| SOLUSDT | 2024 | 1,098 | 36.7 % | 22.7 % | 40.6 % | 13.62 | 10.95 |
| SOLUSDT | 2025 | 1,095 | 19.3 % | 0.2 % | 80.5 % | 0.35 | 2.30 |
| SOLUSDT | 2026* (256 d) | 769 | 12.0 % | 0.0 % | 88.0 % | -1.53 | -0.03 |
| HYPEUSDT | 2025* (216 d) | 1,293 | 71.5 % | 16.3 % | 12.1 % | 13.38 | 10.95 |
| HYPEUSDT | 2026* (256 d) | 1,536 | 49.8 % | 1.1 % | 49.1 % | 4.45 | 10.95 |

## 5. Hyperliquid vs. Binance on the same market and period

![Venues](../figures/fig3-venue-comparison.png)

*Figure 3 — 30-day trailing means of the annualised rate per Binance settlement window, Hyperliquid hourly rates summed into the same windows.*

| Market | Overlap (UTC) | Windows | HL mean %/yr | Binance mean %/yr | HL − Binance (pp) | Mean abs. diff (pp) | Corr. | Windows HL > Binance |
|---|---|---|---|---|---|---|---|---|
| BTC | 2023-05-12 00:00 → 2026-09-13 16:00 | 3,660 | 13.99 | 7.26 | +6.73 | 10.74 | 0.652 | 77.9 % |
| ETH | 2023-05-12 00:00 → 2026-09-13 16:00 | 3,660 | 14.15 | 7.31 | +6.83 | 10.82 | 0.637 | 77.1 % |
| SOL | 2023-05-12 00:00 → 2026-09-13 16:00 | 3,660 | 12.13 | 4.95 | +7.18 | 14.68 | 0.745 | 68.9 % |
| HYPE | 2025-05-30 12:00 → 2026-09-13 20:00 | 2,828 | 12.29 | 8.53 | +3.76 | 9.01 | 0.036 | 45.7 % |

By calendar year (days = overlap days in that year; * partial):

| Market | Year | Windows | HL mean %/yr | Binance mean %/yr | HL − Binance (pp) | Corr. |
|---|---|---|---|---|---|---|
| BTC | 2023* (233 d) | 700 | 13.45 | 8.17 | +5.28 | 0.497 |
| BTC | 2024 (366 d) | 1,097 | 24.17 | 11.94 | +12.23 | 0.700 |
| BTC | 2025 (365 d) | 1,095 | 10.64 | 5.13 | +5.51 | 0.396 |
| BTC | 2026* (256 d) | 768 | 4.73 | 2.78 | +1.95 | 0.428 |
| ETH | 2023* (233 d) | 700 | 19.98 | 8.34 | +11.64 | 0.597 |
| ETH | 2024 (366 d) | 1,097 | 22.12 | 12.97 | +9.15 | 0.664 |
| ETH | 2025 (365 d) | 1,095 | 8.53 | 4.93 | +3.61 | 0.394 |
| ETH | 2026* (256 d) | 768 | 5.44 | 1.70 | +3.74 | 0.532 |
| SOL | 2023* (233 d) | 700 | 11.63 | 5.64 | +5.99 | 0.688 |
| SOL | 2024 (366 d) | 1,097 | 28.21 | 13.63 | +14.58 | 0.805 |
| SOL | 2025 (365 d) | 1,095 | 5.31 | 0.35 | +4.96 | 0.777 |
| SOL | 2026* (256 d) | 768 | -0.66 | -1.53 | +0.87 | 0.756 |
| HYPE | 2025* (216 d) | 1,293 | 16.15 | 13.38 | +2.76 | -0.149 |
| HYPE | 2026* (256 d) | 1,535 | 9.05 | 4.45 | +4.60 | 0.409 |

## 6. Distribution by year: the regime change

![Distribution](../figures/fig4-distribution-by-year.png)

*Figure 4 — per-settlement annualised rate by calendar year: p5–p95, p25–p75, median, hour-weighted mean; dashed = base.*

Binance per calendar year, %/yr:

| Symbol | Year | Mean | Median | p5 | p25 | p75 | p95 | Min | Max |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 2019* (113 d) | 7.48 | 10.95 | -16.6 | 7.74 | 10.95 | 15.5 | -57 | 86 |
| BTCUSDT | 2020 | 17.19 | 10.95 | -14.2 | 10.95 | 14.60 | 74.8 | -328 | 328 |
| BTCUSDT | 2021 | 30.61 | 10.95 | -5.7 | 10.95 | 41.26 | 120.3 | -98 | 273 |
| BTCUSDT | 2022 | 4.16 | 5.62 | -8.5 | 0.64 | 10.95 | 10.9 | -130 | 11 |
| BTCUSDT | 2023 | 7.87 | 9.05 | -1.7 | 3.16 | 10.95 | 16.1 | -12 | 60 |
| BTCUSDT | 2024 | 11.92 | 10.95 | -1.8 | 5.67 | 10.95 | 37.7 | -12 | 97 |
| BTCUSDT | 2025 | 5.13 | 5.28 | -2.6 | 2.04 | 9.09 | 10.9 | -13 | 11 |
| BTCUSDT | 2026* (256 d) | 2.79 | 3.37 | -6.9 | -0.37 | 6.59 | 10.9 | -17 | 11 |
| ETHUSDT | 2019* (35 d) | 8.91 | 10.95 | 0.2 | 10.95 | 10.95 | 10.9 | -25 | 11 |
| ETHUSDT | 2020 | 27.41 | 10.95 | 8.1 | 10.95 | 33.56 | 98.7 | -309 | 402 |
| ETHUSDT | 2021 | 37.54 | 10.95 | 1.5 | 10.95 | 47.22 | 156.8 | -390 | 411 |
| ETHUSDT | 2022 | 0.79 | 4.24 | -17.1 | -3.02 | 10.95 | 10.9 | -331 | 11 |
| ETHUSDT | 2023 | 8.26 | 9.04 | -1.4 | 3.37 | 10.95 | 18.0 | -19 | 78 |
| ETHUSDT | 2024 | 12.96 | 10.95 | 0.6 | 7.01 | 10.95 | 40.4 | -12 | 111 |
| ETHUSDT | 2025 | 4.93 | 5.26 | -2.9 | 1.56 | 9.24 | 10.9 | -28 | 11 |
| ETHUSDT | 2026* (256 d) | 1.70 | 2.58 | -9.0 | -1.24 | 5.84 | 10.8 | -40 | 11 |
| SOLUSDT | 2020* (109 d) | -12.52 | 10.95 | -151.9 | -0.22 | 10.95 | 32.7 | -459 | 142 |
| SOLUSDT | 2021 | 28.59 | 10.95 | 1.5 | 10.95 | 43.86 | 145.1 | -821 | 364 |
| SOLUSDT | 2022 | -38.00 | 1.43 | -311.4 | -13.19 | 10.95 | 10.9 | -8760 | 11 |
| SOLUSDT | 2023 | 1.30 | 10.95 | -23.7 | -2.13 | 10.95 | 26.3 | -1015 | 94 |
| SOLUSDT | 2024 | 13.62 | 10.95 | -3.0 | 5.00 | 10.95 | 51.4 | -20 | 131 |
| SOLUSDT | 2025 | 0.35 | 2.30 | -14.3 | -3.93 | 9.22 | 10.9 | -332 | 28 |
| SOLUSDT | 2026* (256 d) | -1.53 | -0.03 | -20.8 | -6.10 | 5.86 | 10.9 | -76 | 11 |
| HYPEUSDT | 2025* (216 d) | 13.38 | 10.95 | -2.5 | 10.95 | 10.95 | 42.7 | -143 | 433 |
| HYPEUSDT | 2026* (256 d) | 4.45 | 10.95 | -18.1 | 0.59 | 10.95 | 10.9 | -60 | 103 |

## 7. Reading of the results

- **The point mass is the dominant feature.** Over the whole retained history the share of hours settled at
  exactly the base ranges from 40.6 % (SOL) to 76.8 % (PURR); the median annualised rate is 10.95 %/yr (the base itself) in all 8 full calendar market-years of Hyperliquid (§3). Means are driven by the two tails, not by the centre.
- **The tails have thinned on the upside.** For BTC/ETH/SOL the share of hours strictly above the base was
  37.3 % / 36.3 % / 41.1 % in 2024 and is 0.7 % / 0.2 % /
  0.7 % in 2026 (partial, 256 d). Hour-weighted means went from
  24.14 / 22.05 / 28.14 %/yr to 4.73 / 5.44 / -0.67 %/yr.
  In 2026 the below-base tail dominates: 58.0 % (BTC), 51.6 % (ETH),
  67.7 % (SOL) of hours.
- **The regime change is visible on Binance, the only venue with pre-2023 data.** BTCUSDT / ETHUSDT / SOLUSDT
  averaged 30.61 / 37.54 / 28.59 %/yr in 2021, 4.16 / 0.79 /
  -38.00 %/yr in 2022, 11.92 / 12.96 / 13.62 %/yr in 2024 and
  2.79 / 1.70 / -1.53 %/yr in 2026 (partial). The path is not monotonic: 2022 was
  already at or below the 2026 level and 2024 rebounded above the base.
- **Venue.** Over the full overlap Hyperliquid settles higher than Binance on the same market by
  +6.73 / +6.83 / +7.18 pp (BTC / ETH / SOL), with window-level correlations of
  0.65 / 0.64 / 0.75: the two venues move together and the decline appears on both
  (§5, by year). The venue is therefore not what makes the recent funding low; if anything Binance is lower.
- **Extreme values are cadence artefacts of annualisation, not errors.** SOLUSDT's 2022 minimum of
  -8760 %/yr is the −2 % cap settled at the 2 h cadence of November 2022 (−0.02 × 4,380). Such values
  are why medians and shares are reported alongside means.

<!-- u3bis:start -->

## 8. U3-bis — clamp censoring, the venue differential and the HYPE anomaly

Generated 2026-09-14T23:38:22+00:00 by `scripts/analyse_clamp.py` from `data/full/`, under the rules of §1. This section uses the `premium` field that Hyperliquid's `fundingHistory` returns next to `fundingRate`. Binance's `fapi/v1/fundingRate` does not expose its premium index, so everything about the premium below is **Hyperliquid only**; the cross-venue tests use only the settled rates of both venues. The premium is on the 8 h basis (the documented formula's units) and is quoted in basis points per 8 h (bp); the settled rate is put on the same basis (hourly rate × 8, or the rate itself in the 8 h regime of May–June 2023).

### 8.1 The clamp band was not constant: regimes inferred from the data

For every settlement not at the base the formula F = P + clamp(r − P, −c, c) puts F exactly c away from P, so |P − F| reveals c. Runs of ≥ 24 consecutive off-base settlements with the same implied c define the regimes; a regime starts at the first settlement the previous c cannot reproduce. Every settlement is then checked against the formula with its regime's c (tolerance 1e-9):

| Market | c (half-width, 8 h basis) | From (UTC) | To (UTC) | Settlements | Not reproduced | Span of those |
|---|---|---|---|---|---|---|
| BTC | 3 bp | 2023-05-12 00:00 | 2023-06-16 20:00 | 294 | 0 | — |
| BTC | 0 (F = P) | 2023-06-16 21:00 | 2023-07-15 02:00 | 677 | 0 | — |
| BTC | 3 bp | 2023-07-15 03:00 | 2023-12-11 22:00 | 3,595 | 1 | 2023-07-16 01:00 → 2023-07-16 01:00 |
| BTC | 5 bp | 2023-12-11 23:00 | 2026-09-13 23:00 | 24,168 | 0 | — |
| ETH | 3 bp | 2023-05-12 00:00 | 2023-06-16 20:00 | 294 | 0 | — |
| ETH | 0 (F = P) | 2023-06-16 21:00 | 2023-07-15 02:00 | 677 | 0 | — |
| ETH | 3 bp | 2023-07-15 03:00 | 2023-12-11 22:00 | 3,595 | 7 | 2023-07-16 01:00 → 2023-07-16 14:00 |
| ETH | 5 bp | 2023-12-11 23:00 | 2026-09-13 23:00 | 24,168 | 0 | — |
| SOL | 3 bp | 2023-05-12 00:00 | 2023-06-16 20:00 | 294 | 0 | — |
| SOL | 0 (F = P) | 2023-06-16 21:00 | 2023-07-15 02:00 | 677 | 0 | — |
| SOL | 3 bp | 2023-07-15 03:00 | 2023-12-11 22:00 | 3,595 | 0 | — |
| SOL | 5 bp | 2023-12-11 23:00 | 2026-09-13 23:00 | 24,168 | 0 | — |
| HYPE | 5 bp | 2024-12-05 10:00 | 2026-09-13 23:00 | 15,542 | 0 | — |
| PURR | 5 bp | 2024-11-04 10:00 | 2026-09-13 23:00 | 16,286 | 0 | — |

The formula reproduces 118,022 of 118,030 Hyperliquid settlements exactly under the inferred c(t); the 8 it does not reproduce are listed in the table (spans), and the short runs the regime rule ignored are BTC 2023-07-16 01:00 → 2023-07-16 01:00 (1 settlement with implied c = 2 bp), ETH 2023-07-16 01:00 → 2023-07-16 14:00 (7 settlements with implied c = 2 bp). The regime boundaries coincide to the hour across BTC, ETH and SOL, i.e. they are venue-wide; HYPE and PURR were listed after the last change and have a single regime. Consequences: (i) the documented ±0.05 % band (docs/01 §7) holds from 2023-12-11 23:00 UTC onward; before that it was ±0.03 %, and for 677 hours (2023-06-16 21:00 → 2023-07-15 02:00) the settled rate equalled the premium with no interest component and no clamp, so no hour of that period can be 'at base'; (ii) the §2 classification is unchanged (it compares the settled rate with the base and does not depend on c), but 'at base' now means 'premium inside [r − c(t), r + c(t)]' with the c(t) of this table. These regime changes are inferred from the data; no announcement was looked up for them.

### 8.2 Task 1 — how much of the premium the settled series censors

Per market and calendar year: hour-weighted share of hours settled exactly at the base; distribution of the premium conditional on those hours (bp per 8 h); the share of the premium's variance that the settled series does not transmit, 1 − Var(F) / Var(P) with F on the premium's basis (F is a 1-Lipschitz function of P, so the ratio lies in [0, 1]); and the share of the premium's total sum of squares that falls in anchored hours.

| Market | Year | Hours at base | Anchored settlements | Premium in anchored hours: p5 / p25 / p50 / p75 / p95 (bp) | mean ± sd (bp) | Premium sd, all hours (bp) | Variance not transmitted | SS in anchored hours | corr(F, P) |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 2023* (234 d) | 30.2 % | 1,578 | -1.72 / -0.25 / 1.29 / 2.54 / 3.78 | 1.16 ± 1.78 | 4.77 | 71.6 % | 4.2 % | 0.90 |
| BTC | 2024 | 55.3 % | 4,860 | -3.33 / -1.00 / 1.24 / 3.81 / 5.59 | 1.30 ± 2.85 | 5.55 | 74.6 % | 26.5 % | 0.83 |
| BTC | 2025 | 66.1 % | 5,789 | -3.76 / -2.52 / -0.41 / 2.05 / 5.11 | -0.06 ± 2.79 | 4.25 | 92.8 % | 28.8 % | 0.71 |
| BTC | 2026* (256 d) | 41.3 % | 2,535 | -3.92 / -3.51 / -2.72 / -1.35 / 1.61 | -2.15 ± 1.85 | 2.12 | 87.8 % | 54.5 % | 0.70 |
| BTC | all | 50.8 % | 14,762 | -3.76 / -2.33 / -0.16 / 2.42 / 5.27 | 0.16 ± 2.85 | 5.23 | 83.5 % | 15.1 % | 0.81 |
| ETH | 2023* (234 d) | 33.8 % | 1,668 | -1.86 / -1.16 / 0.14 / 2.05 / 3.76 | 0.52 ± 1.90 | 5.18 | 66.0 % | 6.6 % | 0.91 |
| ETH | 2024 | 51.1 % | 4,484 | -3.55 / -1.67 / 0.61 / 3.55 / 5.62 | 0.89 ± 2.96 | 5.74 | 82.3 % | 21.4 % | 0.84 |
| ETH | 2025 | 55.9 % | 4,898 | -3.81 / -2.77 / -0.65 / 1.82 / 5.16 | -0.23 ± 2.83 | 4.34 | 92.3 % | 26.4 % | 0.75 |
| ETH | 2026* (256 d) | 48.2 % | 2,960 | -3.92 / -3.49 / -2.57 / -0.91 / 2.36 | -1.91 ± 2.00 | 2.19 | 88.1 % | 64.6 % | 0.67 |
| ETH | all | 48.6 % | 14,010 | -3.79 / -2.58 / -0.62 / 1.96 / 5.13 | -0.14 ± 2.81 | 5.31 | 84.1 % | 13.7 % | 0.83 |
| SOL | 2023* (234 d) | 20.8 % | 1,126 | -1.84 / -1.03 / 0.05 / 1.64 / 3.78 | 0.45 ± 1.83 | 6.98 | 53.5 % | 1.4 % | 0.96 |
| SOL | 2024 | 48.3 % | 4,244 | -3.20 / -0.63 / 1.66 / 4.12 / 5.62 | 1.57 ± 2.82 | 6.36 | 68.9 % | 18.9 % | 0.87 |
| SOL | 2025 | 51.7 % | 4,533 | -3.82 / -2.87 / -1.20 / 1.09 / 4.85 | -0.61 ± 2.68 | 4.96 | 70.1 % | 18.8 % | 0.77 |
| SOL | 2026* (256 d) | 31.7 % | 1,945 | -3.92 / -3.44 / -2.49 / -0.67 / 3.70 | -1.64 ± 2.36 | 2.67 | 75.5 % | 54.9 % | 0.76 |
| SOL | all | 40.6 % | 11,848 | -3.76 / -2.40 / -0.36 / 2.36 / 5.31 | 0.10 ± 2.88 | 6.40 | 71.4 % | 8.2 % | 0.87 |
| HYPE | 2024* (27 d) | 15.5 % | 99 | -1.31 / 1.69 / 3.54 / 4.92 / 5.77 | 3.03 ± 2.28 | 10.66 | 12.5 % | 21.3 % | 0.99 |
| HYPE | 2025 | 64.5 % | 5,654 | -3.12 / -0.62 / 1.21 / 3.45 / 5.50 | 1.31 ± 2.62 | 5.94 | 62.4 % | 19.6 % | 0.85 |
| HYPE | 2026* (256 d) | 73.1 % | 4,493 | -3.64 / -2.34 / -0.62 / 1.35 / 4.46 | -0.30 ± 2.47 | 3.67 | 92.0 % | 35.9 % | 0.71 |
| HYPE | all | 65.9 % | 10,246 | -3.47 / -1.53 / 0.41 / 2.69 / 5.29 | 0.62 ± 2.68 | 6.45 | 62.2 % | 14.8 % | 0.86 |
| PURR | 2024* (58 d) | 30.9 % | 427 | -1.13 / 0.00 / 0.74 / 3.13 / 5.32 | 1.54 ± 2.11 | 18.95 | 13.3 % | 21.8 % | 0.99 |
| PURR | 2025 | 80.1 % | 7,014 | -0.21 / 0.00 / 0.08 / 1.57 / 4.78 | 0.96 ± 1.64 | 8.76 | 29.3 % | 9.0 % | 0.97 |
| PURR | 2026* (256 d) | 82.4 % | 5,063 | -0.30 / 0.00 / 0.00 / 0.15 / 3.67 | 0.43 ± 1.32 | 10.17 | 28.2 % | 4.6 % | 0.98 |
| PURR | all | 76.8 % | 12,504 | -0.27 / 0.00 / 0.00 / 1.02 / 4.51 | 0.76 ± 1.57 | 11.27 | 26.2 % | 8.7 % | 0.98 |

![Censoring](../figures/fig5-clamp-censoring.png)

*Figure 5 — top: settled rate against the hourly premium for the c = 5 bp regime; the flat segment is the clamp band. Bottom: p5–p95 / p25–p75 / median of the premium during anchored hours, per year; the label is the share of hours at base.*

Reading: during anchored hours the settled rate is a constant and carries no information about where the premium sits inside the band; the premium in those hours spans the whole band (p5–p95 of -3.76 to 5.27 bp for BTC over the whole history, band -4 to +6 bp since 2023-12-11 23:00). Over the whole history the settled series fails to transmit between 26 % (PURR) and 84 % (ETH) of the premium's variance. The funding series is therefore an interval-censored observation of the premium: exact outside the band (shifted by c), censored to the interval inside it. Any use of the settled series as a positioning signal, or any backtest of funding capture built on it, is working with that censored variable, and the censoring is heaviest precisely in the calm regime (2025–2026), when most hours are anchored.

### 8.3 Task 2 — does the averaging window explain the venue differential?

Hypothesis: the Hyperliquid premium is averaged over 1 h, Binance's over 8 h; a shorter window means a higher-variance premium, more mass outside the clamp band, and (if the premium is right-skewed) a higher settled mean. Four measurements follow.

**(a) Skew of the Hyperliquid premium** (Fisher moment skewness of the hourly premium, all hours; mean, median, and share of hours with premium above r):

| Market | Year | Skew | Mean (bp) | Median (bp) | Hours with P > r |
|---|---|---|---|---|---|
| BTC | 2023* (234 d) | +0.62 | +1.01 | +1.42 | 48.2 % |
| BTC | 2024 | +0.47 | +3.87 | +4.03 | 66.5 % |
| BTC | 2025 | +0.82 | -0.40 | -1.30 | 32.6 % |
| BTC | 2026* (256 d) | +2.03 | -3.73 | -4.29 | 3.4 % |
| BTC | all | +0.92 | +0.45 | -0.67 | 39.6 % |
| ETH | 2023* (234 d) | +0.70 | +1.83 | +1.60 | 49.6 % |
| ETH | 2024 | +0.07 | +3.14 | +3.34 | 59.9 % |
| ETH | 2025 | +0.82 | -1.18 | -2.62 | 27.4 % |
| ETH | 2026* (256 d) | +1.38 | -3.48 | -4.05 | 5.4 % |
| ETH | all | +0.79 | +0.21 | -1.31 | 36.8 % |
| SOL | 2023* (234 d) | +0.89 | +0.42 | -0.62 | 36.5 % |
| SOL | 2024 | +0.32 | +4.37 | +4.64 | 68.6 % |
| SOL | 2025 | -5.15 | -1.95 | -3.18 | 21.5 % |
| SOL | 2026* (256 d) | +1.35 | -4.25 | -4.67 | 5.3 % |
| SOL | all | +0.11 | -0.08 | -1.88 | 35.1 % |
| HYPE | 2024* (27 d) | +0.81 | +15.32 | +13.57 | 96.1 % |
| HYPE | 2025 | -0.86 | +3.28 | +2.65 | 62.5 % |
| HYPE | 2026* (256 d) | +0.80 | -0.99 | -1.46 | 26.0 % |
| HYPE | all | +0.92 | +2.09 | +0.92 | 49.5 % |
| PURR | 2024* (58 d) | +2.02 | +17.33 | +12.59 | 82.1 % |
| PURR | 2025 | -3.22 | +3.39 | +0.43 | 43.3 % |
| PURR | 2026* (256 d) | +0.28 | +2.45 | +0.00 | 27.4 % |
| PURR | all | +0.83 | +4.22 | +0.19 | 40.6 % |

**(b) Hours outside the clamp band**, upper tail (P > r + c) and lower tail (P < r − c), hour-weighted, with the c(t) of §8.1. By construction these coincide with the 'above' and 'below' classes of §2; the last column counts the settlements where they do not (the transition hours of §8.1):

| Market | Year | Upper tail | Lower tail | In band | Disagreements with §2 |
|---|---|---|---|---|---|
| BTC | 2023* (234 d) | 32.1 % | 37.7 % | 30.2 % | 1 |
| BTC | 2024 | 37.3 % | 7.3 % | 55.3 % | 0 |
| BTC | 2025 | 10.2 % | 23.7 % | 66.1 % | 0 |
| BTC | 2026* (256 d) | 0.7 % | 58.0 % | 41.3 % | 0 |
| BTC | all | 20.5 % | 28.7 % | 50.8 % | 1 |
| ETH | 2023* (234 d) | 37.6 % | 28.5 % | 33.8 % | 7 |
| ETH | 2024 | 36.3 % | 12.7 % | 51.1 % | 0 |
| ETH | 2025 | 9.3 % | 34.7 % | 55.9 % | 0 |
| ETH | 2026* (256 d) | 0.2 % | 51.6 % | 48.2 % | 0 |
| ETH | all | 20.9 % | 30.5 % | 48.6 % | 7 |
| SOL | 2023* (234 d) | 29.9 % | 49.3 % | 20.8 % | 0 |
| SOL | 2024 | 41.1 % | 10.6 % | 48.3 % | 0 |
| SOL | 2025 | 8.1 % | 40.1 % | 51.7 % | 0 |
| SOL | 2026* (256 d) | 0.7 % | 67.7 % | 31.7 % | 0 |
| SOL | all | 20.6 % | 38.8 % | 40.6 % | 0 |
| HYPE | 2024* (27 d) | 83.9 % | 0.6 % | 15.5 % | 0 |
| HYPE | 2025 | 28.4 % | 7.1 % | 64.5 % | 0 |
| HYPE | 2026* (256 d) | 4.8 % | 22.1 % | 73.1 % | 0 |
| HYPE | all | 21.3 % | 12.7 % | 65.9 % | 0 |
| PURR | 2024* (58 d) | 67.6 % | 1.5 % | 30.9 % | 0 |
| PURR | 2025 | 18.7 % | 1.2 % | 80.1 % | 0 |
| PURR | 2026* (256 d) | 14.6 % | 3.0 % | 82.4 % | 0 |
| PURR | all | 21.3 % | 1.9 % | 76.8 % | 0 |

**(c) Re-aggregation to the Binance settlement windows.** The Hyperliquid hourly rates summed over each Binance window (the §5 method) give, by construction, the same hour-weighted mean as the hourly series over the same hours, so the differential is invariant to the settlement frequency:

| Market | Windows | HL hourly mean, same hours (%/yr) | HL re-aggregated mean (%/yr) | Binance mean (%/yr) | HL − Binance (pp) |
|---|---|---|---|---|---|
| BTC | 3,660 | 13.99 | 13.99 | 7.26 | +6.73 |
| ETH | 3,660 | 14.15 | 14.15 | 7.31 | +6.83 |
| SOL | 3,660 | 12.13 | 12.13 | 4.95 | +7.18 |
| HYPE | 2,828 | 12.29 | 12.29 | 8.53 | +3.76 |

**(d) Counterfactual with the premium averaged over the Binance window.** For every Binance window the Hyperliquid hourly premiums are averaged, the clamp formula (with the regime's c) is applied once to that average, and the result is scaled to the window length. This is what Hyperliquid would have settled had it used Binance's averaging window and its own premium. The difference actual − counterfactual isolates the averaging-window effect; counterfactual − Binance is what it leaves unexplained:

| Market | Overlap (UTC) | Windows | HL actual %/yr | HL counterfactual %/yr | Binance %/yr | HL − Binance (pp) | Window effect (pp) | Residual (pp) | Share explained | Premium sd hourly → window-avg (bp) |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 2023-05-12 00:00 → 2026-09-13 16:00 | 3,660 | 13.99 | 13.82 | 7.26 | +6.73 | +0.18 | +6.56 | +2.6 % | 5.25 → 5.04 |
| ETH | 2023-05-12 00:00 → 2026-09-13 16:00 | 3,660 | 14.15 | 14.07 | 7.31 | +6.83 | +0.07 | +6.76 | +1.1 % | 5.31 → 5.10 |
| SOL | 2023-05-12 00:00 → 2026-09-13 16:00 | 3,660 | 12.13 | 12.14 | 4.95 | +7.18 | -0.01 | +7.19 | -0.2 % | 6.44 → 6.10 |
| HYPE | 2025-05-30 12:00 → 2026-09-13 20:00 | 2,828 | 12.29 | 12.19 | 8.53 | +3.76 | +0.11 | +3.65 | +2.9 % | 4.74 → 4.28 |

By calendar year (correlation with Binance of the actual / counterfactual Hyperliquid series):

| Market | Year | Windows | HL − Binance (pp) | Window effect (pp) | Residual (pp) | Share explained | Corr. actual / counterfactual |
|---|---|---|---|---|---|---|---|
| BTC | 2023* (233 d) | 700 | +5.28 | +0.18 | +5.10 | +3 % | 0.497 / 0.489 |
| BTC | 2024 (366 d) | 1,097 | +12.23 | +0.89 | +11.34 | +7 % | 0.700 / 0.696 |
| BTC | 2025 (365 d) | 1,095 | +5.51 | -0.14 | +5.64 | -2 % | 0.396 / 0.361 |
| BTC | 2026* (256 d) | 768 | +1.95 | -0.40 | +2.36 | -21 % | 0.428 / 0.414 |
| ETH | 2023* (233 d) | 700 | +11.64 | +0.14 | +11.50 | +1 % | 0.597 / 0.589 |
| ETH | 2024 (366 d) | 1,097 | +9.15 | +0.67 | +8.49 | +7 % | 0.664 / 0.664 |
| ETH | 2025 (365 d) | 1,095 | +3.61 | -0.24 | +3.84 | -7 % | 0.394 / 0.372 |
| ETH | 2026* (256 d) | 768 | +3.74 | -0.39 | +4.13 | -11 % | 0.532 / 0.521 |
| SOL | 2023* (233 d) | 700 | +5.99 | +0.11 | +5.87 | +2 % | 0.688 / 0.684 |
| SOL | 2024 (366 d) | 1,097 | +14.58 | +0.79 | +13.79 | +5 % | 0.805 / 0.808 |
| SOL | 2025 (365 d) | 1,095 | +4.96 | -0.58 | +5.53 | -12 % | 0.777 / 0.768 |
| SOL | 2026* (256 d) | 768 | +0.87 | -0.48 | +1.34 | -55 % | 0.756 / 0.755 |
| HYPE | 2025* (216 d) | 1,293 | +2.76 | +0.73 | +2.04 | +26 % | -0.149 / -0.152 |
| HYPE | 2026* (256 d) | 1,535 | +4.60 | -0.42 | +5.02 | -9 % | 0.409 / 0.372 |

The same counterfactual on a fixed 8 h grid (00:00 / 08:00 / 16:00 UTC) for all five Hyperliquid markets, Binance not needed:

| Market | 8 h windows | Actual %/yr | Counterfactual %/yr | Window effect (pp) | By year (pp) |
|---|---|---|---|---|---|
| BTC | 3,660 | 13.99 | 13.82 | +0.18 | 2023: +0.18, 2024: +0.89, 2025: -0.14, 2026: -0.40 |
| ETH | 3,660 | 14.15 | 14.07 | +0.07 | 2023: +0.14, 2024: +0.67, 2025: -0.24, 2026: -0.39 |
| SOL | 3,660 | 12.13 | 12.14 | -0.01 | 2023: +0.11, 2024: +0.79, 2025: -0.58, 2026: -0.48 |
| HYPE | 1,941 | 20.80 | 19.58 | +1.22 | 2024: +4.75, 2025: +2.33, 2026: -0.72 |
| PURR | 2,034 | 37.58 | 32.32 | +5.26 | 2024: +11.79, 2025: +4.02, 2026: +5.57 |

![Decomposition](../figures/fig6-venue-decomposition.png)

*Figure 6 — top: HL − Binance per year split into the averaging-window effect and the residual; bottom: BTC, 30-day trailing means of the actual, counterfactual and Binance series.*

Verdict: the hypothesis is **rejected**. The ingredients it needs are present: the hourly premium is right-skewed over the whole history (BTC +0.92, ETH +0.79, SOL +0.11) and averaging over the window does reduce its dispersion (BTC 5.25 → 5.04 bp, ETH 5.31 → 5.10 bp, SOL 6.44 → 6.10 bp). But the reduction is small, because the hourly premium is persistent within a window, and the clamp is flat inside the band, so the counterfactual mean barely moves: the averaging-window effect is BTC +0.18 pp, ETH +0.07 pp, SOL -0.01 pp against differentials of BTC +6.73 pp, ETH +6.83 pp, SOL +7.18 pp, i.e. it explains +2.6 %, +1.1 %, -0.2 % of them (HYPE: +0.11 of +3.76 pp, +2.9 %). The effect is not even of one sign by year (BTC: 2023 +0.18, 2024 +0.89, 2025 -0.14, 2026 -0.40 pp), so it is not a systematic premium. Re-aggregation (c) cannot change the mean at all. What remains unexplained is BTC +6.56 pp, ETH +6.76 pp, SOL +7.19 pp: the Hyperliquid premium itself sits higher and leaves the band upward more often than Binance's settled rates imply (upper-tail hours over the overlap in §8.3(b) versus the Binance 'above base' shares of §4). Since both venues use the same formula, the same interest rate and, since 2023-12-11 23:00, the same ±0.05 % band, the differential is a difference in the premium (mark-versus-reference price) between the two venues, not in the funding mechanics. What drives that premium difference is outside the reach of this dataset.

### 8.4 Task 3 — the HYPE cross-venue correlation

Diagnostics on the Binance-window series of §5 (Hyperliquid hourly rates summed over each Binance window, both annualised). BTC/ETH/SOL are shown as controls:

| Market | Window | N | Pearson | 95 % CI (N) | lag-1 autocorr. HL / BN | N_eff | 95 % CI (N_eff) | Spearman | Pearson, winsorised 1–99 % | Pearson excl. top-1 window | Pearson excl. top-5 windows | Both at base | Pearson excl. both-at-base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HYPE | 4 h | 2,828 | 0.036 | [-0.001, 0.072] | 0.47 / 0.46 | 1,824 | [-0.010, 0.081] | 0.476 | 0.419 | 0.396 | 0.421 | 33.2 % | 0.042 |
| BTC | 8 h | 3,660 | 0.652 | [0.633, 0.670] | 0.84 / 0.82 | 677 | [0.606, 0.693] | 0.555 | 0.644 | 0.655 | 0.648 | 6.9 % | 0.660 |
| ETH | 8 h | 3,660 | 0.637 | [0.617, 0.655] | 0.82 / 0.81 | 739 | [0.592, 0.678] | 0.630 | 0.654 | 0.637 | 0.641 | 6.6 % | 0.644 |
| SOL | 8 h | 3,660 | 0.745 | [0.730, 0.759] | 0.84 / 0.76 | 803 | [0.713, 0.774] | 0.664 | 0.744 | 0.749 | 0.754 | 6.2 % | 0.749 |

Alignment and aggregation (lag = shift of the Hyperliquid window in hours; positive = later):

| Market | Pearson at lag 0 | Best lag | Pearson, 1-day sums | Pearson, 7-day sums | Pearson by year |
|---|---|---|---|---|---|
| HYPE | 0.036 | +2 h → 0.241 | 0.316 (N 470) | 0.556 (N 65) | 2025: -0.15 / 2026: 0.41 |
| BTC | 0.652 | +3 h → 0.660 | 0.723 (N 1,218) | 0.858 (N 170) | 2023: 0.50 / 2024: 0.70 / 2025: 0.40 / 2026: 0.43 |
| ETH | 0.637 | +2 h → 0.639 | 0.704 (N 1,218) | 0.816 (N 170) | 2023: 0.60 / 2024: 0.66 / 2025: 0.39 / 2026: 0.53 |
| SOL | 0.745 | +2 h → 0.749 | 0.792 (N 1,218) | 0.885 (N 170) | 2023: 0.69 / 2024: 0.80 / 2025: 0.78 / 2026: 0.76 |

HYPE by quarter (Pearson / Spearman / hour-weighted means of both venues, %/yr):

| Quarter | Windows | Pearson | Spearman | HL mean | Binance mean |
|---|---|---|---|---|---|
| 2025-Q2 | 189 | +0.314 | +0.330 | 20.24 | 18.31 |
| 2025-Q3 | 552 | +0.280 | +0.377 | 19.37 | 15.05 |
| 2025-Q4 | 552 | -0.701 | +0.244 | 11.52 | 10.03 |
| 2026-Q1 | 540 | +0.357 | +0.316 | 8.59 | 3.76 |
| 2026-Q2 | 545 | +0.400 | +0.503 | 8.78 | 3.06 |
| 2026-Q3 | 450 | +0.482 | +0.463 | 9.92 | 6.96 |

The five windows with the largest |HL − Binance| and the hourly detail of the largest one:

| Window end (UTC) | HL, 4 h sum (%/yr) | Binance (%/yr) |
|---|---|---|
| 2025-10-11 00:00 | -434.1 | +432.9 |
| 2025-05-31 16:00 | +10.9 | -142.6 |
| 2025-07-12 00:00 | +149.5 | +10.9 |
| 2025-09-08 12:00 | +16.2 | +152.4 |
| 2025-09-09 08:00 | +19.3 | +117.7 |

| Hour (UTC) | HL hourly rate | HL annualised (%/yr) | HL premium (bp / 8 h) | c (bp) |
|---|---|---|---|---|
| 2025-10-10 21:00 | 0.0000125 | +11 | +6.0 | 5 |
| 2025-10-10 22:00 | -0.0018662432 | -1635 | -154.3 | 5 |
| 2025-10-10 23:00 | -0.0001408386 | -123 | -16.3 | 5 |
| 2025-10-11 00:00 | 0.0000125 | +11 | +0.9 | 5 |

Binance HYPEUSDT settled 0.00197693 for the 4 h window ending 2025-10-11 00:00 UTC (+433 %/yr).

![HYPE](../figures/fig7-hype-correlation.png)

*Figure 7 — lag scan (all four markets), HYPE correlation by quarter, correlation against aggregation level, scatter of the two venues' HYPE rates per window, and their 30-day means.*

Conclusion: the near-zero Pearson correlation is a real-data feature concentrated in a handful of windows, not a timing artefact. (i) Alignment: the lag scan has no shifted peak that beats lag 0 by more than the controls do (HYPE best lag +2 h at 0.241); the correlation falls below half its maximum only for lags -2…+1 h, a span of 4 h, i.e. one 4 h window, which is what a single extreme hour paired with one Binance settlement produces. (ii) Sample size: N = 2,828, N_eff ≈ 1,824 after the lag-1 autocorrelation; the 95 % interval on N_eff is [-0.010, 0.081], so the Pearson value is not distinguishable from zero, but the rank correlation is 0.476, and after removing the single window ending 2025-10-11 00:00 UTC (HL -434 %/yr against Binance +433 %/yr, opposite signs, -722 % of the sample covariance) Pearson is 0.396; excluding the five most discordant windows, 0.421. (iii) Sub-periods: 5 of 6 quarters have positive Pearson (2025-Q2 +0.31, 2025-Q3 +0.28, 2025-Q4 -0.70, 2026-Q1 +0.36, 2026-Q2 +0.40, 2026-Q3 +0.48); the negative quarter contains that window. (iv) Aggregation: at 1-day and 7-day sums the correlation rises to 0.32 and 0.56, against 0.86 / 0.82 / 0.89 for BTC / ETH / SOL at 7 days. So: the two venues' HYPE funding does co-move, more weakly than for the majors, and the 0.04 headline is produced by a few hours in which the two venues settled large rates of opposite sign, most of all the window ending 2025-10-11 00:00 UTC, when Hyperliquid's hourly rates hit -1635 %/yr while Binance settled +433 %/yr. Why the two venues' marks moved in opposite directions in those hours cannot be established from funding data alone; that part is left unresolved.

<!-- u3bis:end -->
