# U3 — Analysis of the funding-rate series

Generated 2026-09-14T22:16:23+00:00 by `scripts/analyse.py` from `data/full/`. Every number in this document and in the figures is computed by that script; none is typed by hand. Re-running the script regenerates this file, `docs/04-discrepancies.md`, `figures/` and `results/analysis.json`.

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
