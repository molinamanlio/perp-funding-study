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
