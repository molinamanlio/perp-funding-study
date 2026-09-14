# U3 — Discrepancies: recalled figures vs. recomputation

Generated 2026-09-14T23:38:57+00:00 by `scripts/analyse.py`. The recalled figures come from the author's original run over the window 2025-09-10 04:00 → 2026-09-10 03:00 UTC (8,760 hourly Hyperliquid settlements, simple annualisation). They are a checklist, not a target: nothing in the calculation was adjusted to approach them. §1 recomputes each figure on exactly that window from `data/full/`; §2 asks whether each claim holds on the full history.

## 1. Same window, same convention

### 1.1 Annual means (simple annualisation, %/yr)

| Market | Settlements in window | Recalled | Recomputed | Difference (pp) |
|---|---|---|---|---|
| BTC | 8,760 | 6.00 | 6.0023 | +0.0023 |
| ETH | 8,760 | 6.27 | 6.2728 | +0.0028 |
| SOL | 8,760 | -0.04 | -0.0427 | -0.0027 |
| HYPE | 8,760 | 10.34 | 10.3357 | -0.0043 |
| PURR | 8,760 | 24.40 | 24.4014 | +0.0014 |

### 1.2 Share of hours above the base

| Market | Recalled | Recomputed (strictly above) | Difference | Exactly at base | Below |
|---|---|---|---|---|---|
| BTC | ~1.3 % | 1.28 % (112 of 8,760 h) | -0.02 pp | 49.81 % | 48.92 % |
| ETH | ~0.9 % | 0.89 % (78 of 8,760 h) | -0.01 pp | 53.25 % | 45.86 % |

All five markets in the window, for completeness:

| Market | Above | At base | Below | Median %/yr |
|---|---|---|---|---|
| BTC | 1.28 % | 49.81 % | 48.92 % | 10.95 |
| ETH | 0.89 % | 53.25 % | 45.86 % | 10.95 |
| SOL | 1.58 % | 35.97 % | 62.45 % | 5.47 |
| HYPE | 9.28 % | 72.85 % | 17.87 % | 10.95 |
| PURR | 15.15 % | 82.18 % | 2.67 % | 10.95 |

### 1.3 "Funding fell from 30–37 % annualised in 2021 to 2–3 % in 2026"

Recalled: 30–37 %/yr in 2021 and 2–3 %/yr in 2026. Hyperliquid has no 2021 data, so the 2021 figure can only refer to Binance. Hour-weighted means per calendar year, %/yr:

| Series | 2021 | Mean 2021 | 2026 | Mean 2026 | Median 2026 |
|---|---|---|---|---|---|
| Binance BTCUSDT | 2021 | 30.61 | 2026* (256 d) | 2.79 | 3.37 |
| Binance ETHUSDT | 2021 | 37.54 | 2026* (256 d) | 1.70 | 2.58 |
| Binance SOLUSDT | 2021 | 28.59 | 2026* (256 d) | -1.53 | -0.03 |
| Hyperliquid BTC | — | — | 2026* (256 d) | 4.73 | 7.77 |
| Hyperliquid ETH | — | — | 2026* (256 d) | 5.44 | 10.44 |
| Hyperliquid SOL | — | — | 2026* (256 d) | -0.67 | 3.61 |
| Hyperliquid HYPE | — | — | 2026* (256 d) | 9.05 | 10.95 |
| Hyperliquid PURR | — | — | 2026* (256 d) | 25.66 | 10.95 |

### 1.4 "The difference between venues does not explain the phenomenon"

Same window, Hyperliquid hourly rates summed into the Binance settlement windows, %/yr:

| Market | Windows | HL mean | Binance mean | HL − Binance (pp) | Corr. |
|---|---|---|---|---|---|
| BTC | 1,095 | 6.01 | 3.34 | +2.67 | 0.428 |
| ETH | 1,095 | 6.28 | 2.46 | +3.81 | 0.448 |
| SOL | 1,095 | -0.04 | -1.81 | +1.77 | 0.862 |
| HYPE | 2,189 | 10.33 | 6.96 | +3.37 | -0.132 |

### 1.5 Assessment on the window

- **Annual means:** all five recalled means are reproduced; the largest absolute difference is 0.004 pp,
  i.e. rounding to two decimals. The recalled figures were computed on the same 8,760 settlements with the same
  convention.
- **Share of hours above the base:** BTC 1.28 % and ETH 0.89 % against
  the recalled ~1.3 % and ~0.9 %: reproduced. Note what
  the number means: it is the share *strictly above* the base; a further 49.8 % (BTC) and
  53.3 % (ETH) of hours sit *exactly at* the base, so "at or above" would be
  51.1 % and 54.1 %.
- **"30–37 % in 2021 → 2–3 % in 2026":** the 2021 leg can only be Binance and holds for BTCUSDT
  (30.61 %) and ETHUSDT (37.54 %); SOLUSDT was 28.59 %. The 2026 leg holds for
  BTCUSDT (2.79 %) but not for ETHUSDT (1.70 %) or SOLUSDT (-1.53 %), and not on
  Hyperliquid, where 2026 is 4.73 / 5.44 / -0.67 %/yr. Restricted to the window, Binance
  BTCUSDT / ETHUSDT / SOLUSDT average 3.34 / 2.46 /
  -1.81 %/yr. The claim holds as a statement about BTC and ETH on Binance, endpoint to endpoint;
  it does not hold as stated for SOL, for 2026 on ETH, or for Hyperliquid.
- **"The venue difference does not explain the phenomenon":** on the window Hyperliquid is *above* Binance on every
  market (BTC +2.67 pp, ETH +3.81 pp, SOL
  +1.77 pp, HYPE +3.37 pp) and both venues are far below
  their 2021/2024 levels, so low funding is not a Hyperliquid-specific artefact. The claim holds, with the
  quantified caveat that the venues are not interchangeable: a systematic Hyperliquid premium exists.

## 2. Does each claim hold on the full history?

| Claim | On the one-year window | On the full history |
|---|---|---|
| Annual means BTC 6.00 / ETH 6.27 / SOL -0.04 / HYPE 10.34 / PURR 24.40 %/yr | Reproduced (BTC 6.00, ETH 6.27, SOL -0.04, HYPE 10.34, PURR 24.40) | Window-specific. Whole-history hour-weighted means: BTC 14.00, ETH 14.15, SOL 12.13, HYPE 20.89, PURR 37.59 %/yr. |
| BTC above base ~1.3 % of hours, ETH ~0.9 % | Reproduced (1.28 % / 0.89 %) | Holds only for the last year. Whole history: BTC 20.5 %, ETH 20.9 %; 2024: 37.3 % / 36.3 %; 2026 (partial): 0.7 % / 0.2 %. It is a property of the current regime, not of the markets. |
| Funding fell from 30–37 % (2021) to 2–3 % (2026) | 2026 leg on the window: Binance BTCUSDT 3.34 %, ETHUSDT 2.46 %, SOLUSDT -1.81 % | Holds endpoint-to-endpoint for BTCUSDT (30.61 → 2.79) and, with a 2026 value below the stated range, ETHUSDT (37.54 → 1.70); not for SOLUSDT (28.59 → -1.53). It hides that 2022 (4.16 / 0.79 / -38.00) was already low and 2024 (11.92 / 12.96 / 13.62) rebounded. Hyperliquid shows the same 2024 → 2026 fall (24.14 → 4.73 BTC). |
| Venue difference does not explain it | Holds: HL − Binance +2.67 / +3.81 / +1.77 pp (BTC/ETH/SOL), both venues low | Holds: HL − Binance +6.73 / +6.83 / +7.18 pp over the full overlap, correlation 0.65 / 0.64 / 0.75; the decline is on both venues, and Hyperliquid carries a persistent premium over Binance. |

Nothing was adjusted to approach the recalled figures; the recomputed values are the published ones.
