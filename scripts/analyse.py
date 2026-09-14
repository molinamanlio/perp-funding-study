#!/usr/bin/env python3
"""U3 — analysis of the funding-rate series in data/full/.

    .venv/bin/python scripts/analyse.py

Reads ONLY data/full/ (never data/baseline/ or data/downloaded/). Writes:

- figures/*.png and figures/*.svg      the four committed figures + the base-mass figure
- results/analysis.json                every number used in the documents
- docs/03-analysis.md                  analysis document, all numbers interpolated
- docs/04-discrepancies.md             recalled figures vs. recomputed, all numbers interpolated

No number that appears in the two documents is typed by hand: every figure in them is
computed here from data/full/ and formatted by this script. The recalled figures
checked in docs/04 are constants declared in RECALLED below (they are the
checklist, not a target, and are labelled as recalled wherever printed).

Calculation rules are stated in docs/03-analysis.md §1 and implemented in the
functions marked "RULE" below. Requires numpy and matplotlib (see requirements.txt);
the rest is the standard library.
"""
import datetime as dt
import json
import math
import os
import sys
from collections import OrderedDict, defaultdict
from decimal import Decimal

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "full")
FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results")
DOCS = os.path.join(ROOT, "docs")

HL_COINS = ["BTC", "ETH", "SOL", "HYPE", "PURR"]
BN_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT"]
BN_OF = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "HYPE": "HYPEUSDT"}

HOURS_PER_YEAR = 8760          # 365 d × 24 h; simple convention (docs/01 §7)
MS_H = 3_600_000

# RULE: base ("interest rate") component, per hour, exact decimal (docs/01 §7).
HL_BASE_HOURLY = Decimal("0.0000125")          # 0.01 % / 8 h
BN_BASE_8H = Decimal("0.0001")                 # Binance interest rate 0.01 % / 8 h (same per-hour value)
BASE_PER_HOUR = HL_BASE_HOURLY                 # both venues: 0.0000125 per hour

# Baseline window of U1 (the author's original run): 8,760 hourly settlements.
WINDOW_START_MS = 1757476800000   # 2025-09-10 04:00:00 UTC (first baseline record)
WINDOW_END_MS = WINDOW_START_MS + 8759 * 3_600_000   # 2026-09-10 03:00:00 UTC (last baseline record; ms jitter handled by the caller)

# Recalled figures from the author's original run (checklist only, see docs/04).
RECALLED = {
    "annual_mean_pct": {"BTC": 6.00, "ETH": 6.27, "SOL": -0.04, "HYPE": 10.34, "PURR": 24.40},
    "share_hours_above_base_pct": {"BTC": 1.3, "ETH": 0.9},
    "regime_2021_pct": (30.0, 37.0),
    "regime_2026_pct": (2.0, 3.0),
}


def utc(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)


def fmt_ts(ms):
    return utc(ms).strftime("%Y-%m-%d %H:%M")


# --------------------------------------------------------------------------- loading

class Series:
    """One market on one venue.

    t          settlement timestamps (ms, ascending)
    rate_str   the exact decimal strings served by the API
    rate       float per-settlement rate
    ivl_h      RULE: interval in hours assigned to each settlement (observed, see assign_intervals)
    ann        RULE: simple annualised rate = rate × (8760 / ivl_h)
    base_h     base rate per settlement (BASE_PER_HOUR × ivl_h) as Decimal
    base_ann   base annualised under the same convention = BASE_PER_HOUR × 8760 (constant)
    cls        RULE: +1 above base, 0 exactly at base, -1 below base (exact Decimal comparison)
    missing    list of (from_ms, to_ms) omitted settlements inferred inside a cadence run
    """

    def __init__(self, venue, market, path):
        self.venue, self.market, self.path = venue, market, path
        rows = [json.loads(l) for l in open(path)]
        tkey = "time" if venue == "HL" else "fundingTime"
        self.n = len(rows)
        self.t = np.array([r[tkey] for r in rows], dtype=np.int64)
        assert np.all(np.diff(self.t) > 0), f"{path}: timestamps not strictly increasing"
        self.rate_str = [r["fundingRate"] for r in rows]
        self.rate_dec = [Decimal(s) for s in self.rate_str]
        self.rate = np.array([float(s) for s in self.rate_str])
        self.first_ms, self.last_ms = int(self.t[0]), int(self.t[-1])
        self.assign_intervals()
        self.ann = self.rate * (HOURS_PER_YEAR / self.ivl_h)
        self.base_ann = float(BASE_PER_HOUR) * HOURS_PER_YEAR
        base_per_settle = [BASE_PER_HOUR * Decimal(int(round(h))) for h in self.ivl_h]
        self.cls = np.array([(r > b) - (r < b) for r, b in zip(self.rate_dec, base_per_settle)], dtype=np.int8)
        self.year = np.array([utc(int(x)).year for x in self.t])
        self.dt = np.array([utc(int(x)) for x in self.t])

    def assign_intervals(self):
        """RULE: the interval of a settlement is the observed delta to the previous
        settlement, rounded to the nearest hour. Rounding absorbs the sub-second jitter
        and the handful of settlements executed minutes late (the venue then settles
        again at the next hour, so the two deltas sum to the cadence); every delta whose
        raw value departs from the rounded hour by more than 1 s is listed in
        `delayed`. The first record takes the delta to the next one. A *single* delta
        that is a whole multiple (k >= 2) of the cadence on both sides of it is an
        omitted settlement, not a cadence change: that record keeps the run's cadence
        and the k-1 omitted slots are recorded in `missing`. Two or more consecutive
        equal deltas form a cadence run and are annualised with their own interval
        (SOLUSDT Nov 2022; Hyperliquid's 8 h regime of May-June 2023)."""
        d_ms = np.diff(self.t)
        d_h = np.rint(d_ms / MS_H).astype(np.int64)
        assert (d_h >= 1).all(), f"{self.path}: a delta rounds to 0 h"
        self.delayed = [(int(self.t[i]), int(self.t[i + 1]), int(d_ms[i]))
                        for i in range(len(d_ms)) if abs(d_ms[i] - d_h[i] * MS_H) > 60_000]
        self.max_jitter_ms = int(max(abs(d_ms[i] - d_h[i] * MS_H) for i in range(len(d_ms)) if abs(d_ms[i] - d_h[i] * MS_H) <= 60_000))
        runs = []
        i = 0
        while i < len(d_h):
            j = i
            while j + 1 < len(d_h) and d_h[j + 1] == d_h[i]:
                j += 1
            runs.append([i, j, int(d_h[i])])   # deltas i..j inclusive, value in hours
            i = j + 1
        ivl = d_h.astype(float)
        self.missing = []
        self.runs = []
        for k, (i, j, v) in enumerate(runs):
            single = (i == j)
            prev_v = runs[k - 1][2] if k > 0 else None
            next_v = runs[k + 1][2] if k + 1 < len(runs) else None
            if single and prev_v is not None and next_v is not None and prev_v == next_v \
                    and v > prev_v and v % prev_v == 0:
                ivl[i] = prev_v
                for m in range(1, v // prev_v):
                    self.missing.append(int(self.t[i] + m * prev_v * MS_H))
                self.runs.append({"interval_h": v, "from": int(self.t[i]), "to": int(self.t[i + 1]),
                                  "deltas": 1, "treated_as": "omitted settlement", "cadence_h": prev_v})
            else:
                self.runs.append({"interval_h": v, "from": int(self.t[i]), "to": int(self.t[j + 1]),
                                  "deltas": j - i + 1, "treated_as": "cadence run"})
        ivl_h = np.empty(len(self.t))
        ivl_h[1:] = ivl
        ivl_h[0] = ivl[0]
        self.ivl_h = ivl_h
        self.cadence_runs = [r for r in self.runs if r["treated_as"] == "cadence run"]

    # ---- helpers
    def mask_window(self, a, b):
        return (self.t >= a) & (self.t <= b)

    def coverage_hours(self, mask):
        return float(self.ivl_h[mask].sum())


def load_all():
    hl = OrderedDict((c, Series("HL", c, os.path.join(DATA, f"funding-{c}.jsonl"))) for c in HL_COINS)
    bn = OrderedDict((s, Series("BN", s, os.path.join(DATA, f"binance-funding-{s}.jsonl"))) for s in BN_SYMBOLS)
    return hl, bn


# --------------------------------------------------------------------------- statistics

def year_stats(s: Series, years=None):
    """Per calendar year (UTC): coverage, share of settlement-hours above/at/below base,
    simple-annualised mean (hour-weighted), quantiles of the annualised rate."""
    out = OrderedDict()
    years = years or sorted(set(int(y) for y in s.year))
    for y in years:
        m = s.year == y
        if not m.any():
            continue
        w = s.ivl_h[m]
        hours = w.sum()
        days_in_year = 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365
        # RULE: a calendar year is partial when the series does not span it: the first
        # settlement of the year is later than its own interval after Jan 1 00:00 UTC,
        # or the last one is earlier than its own interval before Dec 31 24:00 UTC.
        # Omitted settlements inside a spanned year do not make it partial; they are
        # counted separately in `omitted`.
        y0 = int(dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
        y1 = int(dt.datetime(y + 1, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
        t_first, t_last = int(s.t[m][0]), int(s.t[m][-1])
        partial = (t_first - y0 > s.ivl_h[m][0] * MS_H + 60_000) or (y1 - t_last > s.ivl_h[m][-1] * MS_H + 60_000)
        out[y] = {
            "records": int(m.sum()),
            "hours": float(hours),
            "days": float(hours / 24),
            "partial": bool(partial),
            "omitted": int(sum(1 for x in s.missing if y0 <= x < y1)),
            "days_in_year": days_in_year,
            "first": fmt_ts(int(s.t[m][0])), "last": fmt_ts(int(s.t[m][-1])),
            "share_above_pct": float(100 * w[s.cls[m] > 0].sum() / hours),
            "share_at_pct": float(100 * w[s.cls[m] == 0].sum() / hours),
            "share_below_pct": float(100 * w[s.cls[m] < 0].sum() / hours),
            "n_above": int((s.cls[m] > 0).sum()), "n_at": int((s.cls[m] == 0).sum()), "n_below": int((s.cls[m] < 0).sum()),
            "mean_ann_pct": float(100 * np.average(s.ann[m], weights=w)),
            "median_ann_pct": float(100 * np.median(s.ann[m])),
            "q05_ann_pct": float(100 * np.quantile(s.ann[m], 0.05)),
            "q25_ann_pct": float(100 * np.quantile(s.ann[m], 0.25)),
            "q75_ann_pct": float(100 * np.quantile(s.ann[m], 0.75)),
            "q95_ann_pct": float(100 * np.quantile(s.ann[m], 0.95)),
            "min_ann_pct": float(100 * s.ann[m].min()), "max_ann_pct": float(100 * s.ann[m].max()),
        }
    return out


def window_stats(s: Series, a, b):
    m = s.mask_window(a, b)
    w = s.ivl_h[m]
    hours = w.sum()
    return {
        "records": int(m.sum()), "hours": float(hours),
        "first": fmt_ts(int(s.t[m][0])) if m.any() else None, "last": fmt_ts(int(s.t[m][-1])) if m.any() else None,
        "mean_ann_pct": float(100 * np.average(s.ann[m], weights=w)),
        "mean_ann_unweighted_pct": float(100 * s.ann[m].mean()),
        "median_ann_pct": float(100 * np.median(s.ann[m])),
        "share_above_pct": float(100 * w[s.cls[m] > 0].sum() / hours),
        "share_at_pct": float(100 * w[s.cls[m] == 0].sum() / hours),
        "share_below_pct": float(100 * w[s.cls[m] < 0].sum() / hours),
        "n_above": int((s.cls[m] > 0).sum()), "n_at": int((s.cls[m] == 0).sum()), "n_below": int((s.cls[m] < 0).sum()),
    }


def invariance_check(s: Series):
    """RULE check: the above/at/below counts must be identical whether computed on the
    exact decimal strings, on float per-settlement rates, on simple-annualised floats or
    on compound-annualised floats, each side under the same convention."""
    n = len(s.rate)
    base_settle = np.array([float(BASE_PER_HOUR) * h for h in self_ivl(s)])
    raw_float = np.sign(s.rate - base_settle).astype(np.int8)
    simple = np.sign(s.ann - s.base_ann).astype(np.int8)
    per_year = HOURS_PER_YEAR / s.ivl_h
    comp_obs = (1 + s.rate) ** per_year - 1
    comp_base = (1 + base_settle) ** per_year - 1
    compound = np.sign(comp_obs - comp_base).astype(np.int8)
    def counts(c):
        return {"above": int((c > 0).sum()), "at": int((c == 0).sum()), "below": int((c < 0).sum())}
    res = {"exact_decimal": counts(s.cls), "float_raw": counts(raw_float),
           "float_simple_annualised": counts(simple), "float_compound_annualised": counts(compound)}
    res["all_identical"] = all(res[k] == res["exact_decimal"] for k in res if k != "exact_decimal")
    res["records"] = n
    return res


def self_ivl(s):
    return s.ivl_h


def hl_to_8h(hl: Series, bn: Series):
    """Aggregate Hyperliquid rates into the Binance settlement windows: for each Binance
    settlement at t with interval I, the sum of the Hyperliquid rates of the settlements
    whose hour slot lies in (t − I, t]. A window is kept only when the Hyperliquid
    intervals found inside it sum exactly to I (8 hourly records in the 1 h regime, one
    8 h record in Hyperliquid's own 8 h regime of May–June 2023); windows touching an
    omitted Hyperliquid settlement are dropped."""
    idx = {int(x): i for i, x in enumerate(hl.t // MS_H)}   # hour-slot → index (jitter removed)
    rows = []
    for j in range(len(bn.t)):
        t_slot = int(bn.t[j] // MS_H)
        I = int(round(bn.ivl_h[j]))
        ks = [k for k in (idx.get(t_slot - h) for h in range(I)) if k is not None]
        if not ks or sum(hl.ivl_h[k] for k in ks) != I:
            continue
        hl_sum = float(sum(hl.rate[k] for k in ks))
        rows.append((int(bn.t[j]), I, bn.rate[j], hl_sum))
    t = np.array([r[0] for r in rows], dtype=np.int64)
    I = np.array([r[1] for r in rows], dtype=float)
    bn_r = np.array([r[2] for r in rows])
    hl_r = np.array([r[3] for r in rows])
    return t, I, bn_r, hl_r


def venue_comparison(hl: Series, bn: Series):
    t, I, bn_r, hl_r = hl_to_8h(hl, bn)
    if len(t) == 0:
        return None
    per_year = HOURS_PER_YEAR / I
    bn_ann, hl_ann = bn_r * per_year, hl_r * per_year
    years = np.array([utc(int(x)).year for x in t])
    def block(m):
        w = I[m]
        return {
            "windows": int(m.sum()), "hours": float(w.sum()), "days": float(w.sum() / 24),
            "first": fmt_ts(int(t[m][0])), "last": fmt_ts(int(t[m][-1])),
            "hl_mean_ann_pct": float(100 * np.average(hl_ann[m], weights=w)),
            "bn_mean_ann_pct": float(100 * np.average(bn_ann[m], weights=w)),
            "diff_hl_minus_bn_pct": float(100 * (np.average(hl_ann[m], weights=w) - np.average(bn_ann[m], weights=w))),
            "mean_abs_diff_pct": float(100 * np.average(np.abs(hl_ann[m] - bn_ann[m]), weights=w)),
            "corr": float(np.corrcoef(hl_ann[m], bn_ann[m])[0, 1]) if m.sum() > 2 else float("nan"),
            "share_windows_hl_above_bn_pct": float(100 * (hl_r[m] > bn_r[m]).mean()),
            "share_windows_equal_pct": float(100 * (hl_r[m] == bn_r[m]).mean()),
        }
    res = {"overall": block(np.ones(len(t), bool)), "by_year": OrderedDict()}
    for y in sorted(set(int(y) for y in years)):
        res["by_year"][y] = block(years == y)
    res["series"] = {"t": t, "I": I, "hl_ann": hl_ann, "bn_ann": bn_ann}
    return res


def rolling_mean_days(t_ms, ann, ivl_h, days):
    """Trailing hour-weighted mean over `days` days, evaluated at each settlement."""
    w = ivl_h
    x = ann * w
    cw, cx = np.concatenate([[0], np.cumsum(w)]), np.concatenate([[0], np.cumsum(x)])
    win = days * 24 * MS_H
    start = np.searchsorted(t_ms, t_ms - win, side="right")
    n = np.arange(1, len(t_ms) + 1)
    num = cx[n] - cx[start]
    den = cw[n] - cw[start]
    return num / den



# --------------------------------------------------------------------------- figures

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Fixed categorical slots (never cycled): market identity keeps its hue across figures.
COL = {"BTC": "#2a78d6", "ETH": "#eb6834", "SOL": "#1baf7a", "HYPE": "#eda100", "PURR": "#e87ba4",
       "BTCUSDT": "#2a78d6", "ETHUSDT": "#eb6834", "SOLUSDT": "#1baf7a", "HYPEUSDT": "#eda100"}
VENUE_COL = {"HL": "#2a78d6", "BN": "#eb6834"}
DIV = {"below": "#2a78d6", "at": "#b8b7b2", "above": "#e34948"}   # diverging: blue / neutral / red
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": GRID, "axes.linewidth": 0.8, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2, "text.color": INK,
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False,
    "legend.fontsize": 8, "figure.dpi": 110, "savefig.dpi": 160, "font.family": "DejaVu Sans",
})


def year_label(y, ys):
    st = ys.get(y)
    return f"{y}*\n({st['days']:.0f} d)" if st and st["partial"] else f"{y}"


def savefig(fig, name):
    fig.savefig(os.path.join(FIG, name + ".png"), bbox_inches="tight")
    fig.savefig(os.path.join(FIG, name + ".svg"), bbox_inches="tight")
    plt.close(fig)


def fig_base_mass(hl, ys_hl, hist):
    """Main result: mass at base vs. two tails, per market and year + hourly histogram."""
    fig = plt.figure(figsize=(11, 8.2))
    gs = fig.add_gridspec(2, 5, height_ratios=[1.25, 1], hspace=0.55, wspace=0.35)
    ax = fig.add_subplot(gs[0, :])
    labels, below, at, above = [], [], [], []
    for c in HL_COINS:
        for y, st in ys_hl[c].items():
            labels.append(f"{c} {y}* ({st['days']:.0f} d)" if st["partial"] else f"{c} {y}")
            below.append(st["share_below_pct"]); at.append(st["share_at_pct"]); above.append(st["share_above_pct"])
    ypos = np.arange(len(labels))[::-1]
    ax.barh(ypos, below, color=DIV["below"], height=0.72, label="below base")
    ax.barh(ypos, at, left=below, color=DIV["at"], height=0.72, label="exactly at base")
    ax.barh(ypos, above, left=np.array(below) + np.array(at), color=DIV["above"], height=0.72, label="above base")
    for i, (b, a, u) in enumerate(zip(below, at, above)):
        if a >= 4: ax.text(b + a / 2, ypos[i], f"{a:.0f}%", ha="center", va="center", fontsize=7.5, color=INK)
        if b >= 4: ax.text(b / 2, ypos[i], f"{b:.0f}%", ha="center", va="center", fontsize=7, color="white")
        if u >= 4: ax.text(b + a + u / 2, ypos[i], f"{u:.0f}%", ha="center", va="center", fontsize=7, color="white")
    ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 100); ax.set_xlabel("share of settlement-hours (%)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Hyperliquid funding vs. the base rate: share of hours exactly at, above and below 0.0000125/h\n"
                 "(exact decimal comparison; hour-weighted; * = partial calendar year)", loc="left", pad=22)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=3, borderaxespad=0.0)
    for k, c in enumerate(HL_COINS):
        axh = fig.add_subplot(gs[1, k])
        edges, counts, base_bin = hist[c]["edges"], hist[c]["counts"], hist[c]["base_bin"]
        cols = [DIV["at"] if i == base_bin else COL[c] for i in range(len(counts))]
        axh.bar(edges[:-1], counts, width=np.diff(edges), align="edge", color=cols, linewidth=0)
        axh.set_yscale("log"); axh.set_xlim(edges[0], edges[-1])
        axh.set_title(c, fontsize=9, loc="left")
        axh.set_xlabel("annualised rate (%/yr)"); axh.grid(axis="x", visible=False)
        if k == 0:
            axh.set_ylabel("settlements (log)")
        axh.text(0.98, 0.95, f"bin at base:\n{hist[c]['share_at_pct']:.1f}% of settlements",
                 transform=axh.transAxes, ha="right", va="top", fontsize=7.5, color=INK2)
    savefig(fig, "fig0-base-mass")


def fig_timeseries(hl, days=30):
    fig, axes = plt.subplots(len(HL_COINS), 1, figsize=(11, 10), sharex=True)
    for ax, c in zip(axes, HL_COINS):
        s = hl[c]
        r7 = rolling_mean_days(s.t, s.ann, s.ivl_h, 7) * 100
        r30 = rolling_mean_days(s.t, s.ann, s.ivl_h, days) * 100
        ax.plot(s.dt, r7, color=COL[c], lw=0.6, alpha=0.35)
        ax.plot(s.dt, r30, color=COL[c], lw=1.6, label=f"{c} ({days}-day trailing mean)")
        ax.axhline(s.base_ann * 100, color=INK2, lw=1.0, ls="--", label=f"base {s.base_ann*100:.2f}%/yr")
        ax.axhline(0, color=GRID, lw=0.8)
        lo, hi = np.nanquantile(r7, [0.005, 0.995])
        ax.set_ylim(min(lo, -15), max(hi, 25))
        ax.set_ylabel("%/yr")
        ax.legend(loc="upper left", ncol=2)
        ax.set_title(f"{fmt_ts(s.first_ms)} → {fmt_ts(s.last_ms)} UTC, {s.n:,} settlements",
                     loc="right", fontsize=7.5, color=INK2, fontweight="normal")
    axes[0].set_title("Hyperliquid funding, simple annualisation (rate × settlements/yr from the observed interval), "
                      "hour-weighted trailing means; thin line = 7-day", loc="left", pad=10)
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    savefig(fig, "fig1-timeseries-annualised")


def fig_share_above(ys_hl, ys_bn):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [4, 8]})
    for ax, ys, names, title in ((a1, ys_hl, HL_COINS, "Hyperliquid (base 0.0000125/h)"),
                                 (a2, ys_bn, BN_SYMBOLS, "Binance (base 0.0001/8 h = same per hour)")):
        years = sorted({y for n in names for y in ys[n]})
        x = np.arange(len(years)); w = 0.8 / len(names)
        for k, n in enumerate(names):
            vals = [ys[n][y]["share_above_pct"] if y in ys[n] else np.nan for y in years]
            ax.bar(x + (k - (len(names) - 1) / 2) * w, vals, width=w * 0.92, color=COL[n], label=n, linewidth=0)
        anyys = {y: next(ys[n][y] for n in names if y in ys[n]) for y in years}
        ax.set_xticks(x); ax.set_xticklabels([year_label(y, anyys) for y in years], fontsize=8)
        ax.set_title(title, loc="left"); ax.grid(axis="x", visible=False)
        ax.legend(ncol=len(names), loc="upper center", bbox_to_anchor=(0.5, -0.18))
    a1.set_ylabel("share of hours with funding strictly above base (%)")
    lim = max(a1.get_ylim()[1], a2.get_ylim()[1]); a1.set_ylim(0, lim); a2.set_ylim(0, lim)
    fig.suptitle("Share of hours per calendar year in which funding exceeded the venue base rate "
                 "(* partial year, days covered in brackets)", x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    savefig(fig, "fig2-share-above-base")


def fig_venues(cmp):
    fig, axes = plt.subplots(len(cmp), 1, figsize=(11, 9), sharex=True)
    for ax, (c, r) in zip(axes, cmp.items()):
        sr = r["series"]
        d = np.array([utc(int(x)) for x in sr["t"]])
        for key, lab in (("hl_ann", "Hyperliquid (summed into the Binance windows)"), ("bn_ann", "Binance")):
            v = rolling_mean_days(sr["t"], sr[key], sr["I"], 30) * 100
            ax.plot(d, v, color=VENUE_COL["HL" if key == "hl_ann" else "BN"], lw=1.5, label=lab)
        ax.axhline(float(BASE_PER_HOUR) * HOURS_PER_YEAR * 100, color=INK2, lw=1.0, ls="--", label="base")
        ax.axhline(0, color=GRID, lw=0.8)
        o = r["overall"]
        ax.set_ylabel("%/yr")
        ax.set_title(f"{c}: overlap {o['first']} → {o['last']} UTC, {o['windows']:,} windows — "
                     f"mean HL {o['hl_mean_ann_pct']:.2f}%/yr, Binance {o['bn_mean_ann_pct']:.2f}%/yr, "
                     f"HL − Binance {o['diff_hl_minus_bn_pct']:+.2f} pp, corr {o['corr']:.2f}", loc="left", fontsize=9)
        if ax is axes[0]:
            ax.legend(loc="upper right", ncol=3)
    axes[0].text(0, 1.25, "Hyperliquid vs. Binance on the same market and period: 30-day trailing mean of the "
                 "annualised rate per Binance settlement window", transform=axes[0].transAxes, fontsize=10,
                 fontweight="bold", va="bottom")
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    savefig(fig, "fig3-venue-comparison")


def fig_distribution(ys_hl, ys_bn):
    fig, axes = plt.subplots(3, 3, figsize=(11, 9.5))
    axes = axes.ravel()
    panels = [("HL", c, ys_hl[c]) for c in HL_COINS] + [("BN", s, ys_bn[s]) for s in BN_SYMBOLS]
    for ax, (v, n, ys) in zip(axes, panels):
        years = list(ys)
        x = np.arange(len(years))
        for i, y in enumerate(years):
            st = ys[y]
            ax.plot([i, i], [st["q05_ann_pct"], st["q95_ann_pct"]], color=COL[n], lw=1.2, alpha=0.45, solid_capstyle="round")
            ax.plot([i, i], [st["q25_ann_pct"], st["q75_ann_pct"]], color=COL[n], lw=5, solid_capstyle="butt")
            ax.plot([i - 0.22, i + 0.22], [st["median_ann_pct"]] * 2, color=SURF, lw=1.4)
            ax.plot(i, st["mean_ann_pct"], marker="D", ms=4.5, color=INK, mec=SURF, mew=0.8)
        ax.axhline(float(BASE_PER_HOUR) * HOURS_PER_YEAR * 100, color=INK2, lw=1.0, ls="--")
        ax.axhline(0, color=GRID, lw=0.8)
        ax.set_xticks(x); ax.set_xticklabels([year_label(y, ys) for y in years], fontsize=7.5)
        ax.set_title(f"{'Hyperliquid' if v == 'HL' else 'Binance'} {n}", loc="left")
        ax.grid(axis="x", visible=False)
        ax.set_xlim(-0.6, len(years) - 0.4)
    for ax in axes[len(panels):]:
        ax.axis("off")
    axes[0].set_ylabel("annualised rate (%/yr)"); axes[3].set_ylabel("annualised rate (%/yr)"); axes[6].set_ylabel("annualised rate (%/yr)")
    fig.suptitle("Distribution of the per-settlement annualised funding rate by calendar year: "
                 "p5–p95 (thin), p25–p75 (thick), median (white tick), ◆ hour-weighted mean, dashed = base",
                 x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    savefig(fig, "fig4-distribution-by-year")


def histogram(s: Series, lo=-60, hi=80, step=2.0):
    edges = np.arange(lo, hi + step, step)
    ann_pct = np.clip(s.ann * 100, lo, hi - 1e-9)
    counts, _ = np.histogram(ann_pct, bins=edges)
    base = s.base_ann * 100
    base_bin = int(np.searchsorted(edges, base, side="right") - 1)
    return {"edges": edges, "counts": counts, "base_bin": base_bin,
            "share_at_pct": float(100 * (s.cls == 0).mean()),
            "share_in_base_bin_pct": float(100 * counts[base_bin] / len(ann_pct))}


# --------------------------------------------------------------------------- main

def main():
    os.makedirs(FIG, exist_ok=True); os.makedirs(RES, exist_ok=True)
    hl, bn = load_all()
    R = OrderedDict()
    R["generated_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    R["base_per_hour"] = str(BASE_PER_HOUR); R["base_ann_simple_pct"] = float(BASE_PER_HOUR) * HOURS_PER_YEAR * 100
    R["base_ann_compound_pct"] = ((1 + 0.0001) ** 1095 - 1) * 100

    # dataset inventory + interval runs + irregularities
    inv = OrderedDict()
    for s in list(hl.values()) + list(bn.values()):
        inv[s.venue + ":" + s.market] = {
            "venue": s.venue, "market": s.market, "records": s.n, "first": fmt_ts(s.first_ms), "last": fmt_ts(s.last_ms),
            "hours_covered": float(s.ivl_h.sum()), "years": sorted(set(int(y) for y in s.year)),
            "runs": [{**r, "from_utc": fmt_ts(r["from"]), "to_utc": fmt_ts(r["to"])} for r in s.runs],
            "missing": [fmt_ts(m) for m in s.missing], "max_jitter_ms": s.max_jitter_ms,
            "delayed": [{"from": fmt_ts(a), "to_exact": utc(b).strftime("%Y-%m-%d %H:%M:%S"), "delta_min": d / 60000} for a, b, d in s.delayed],
        }
    R["inventory"] = inv

    ys_hl = OrderedDict((c, year_stats(hl[c])) for c in HL_COINS)
    ys_bn = OrderedDict((k, year_stats(bn[k])) for k in BN_SYMBOLS)
    R["by_year"] = {"HL": ys_hl, "BN": ys_bn}
    R["invariance"] = {"HL": {c: invariance_check(hl[c]) for c in HL_COINS},
                       "BN": {k: invariance_check(bn[k]) for k in BN_SYMBOLS}}
    R["full_history"] = {"HL": {c: window_stats(hl[c], hl[c].first_ms, hl[c].last_ms) for c in HL_COINS},
                         "BN": {k: window_stats(bn[k], bn[k].first_ms, bn[k].last_ms) for k in BN_SYMBOLS}}
    hist = {c: histogram(hl[c]) for c in HL_COINS}
    R["histogram"] = {c: {"share_at_pct": h["share_at_pct"], "share_in_base_bin_pct": h["share_in_base_bin_pct"],
                          "bin_width_pct": float(h["edges"][1] - h["edges"][0])} for c, h in hist.items()}

    # HYPEUSDT omitted settlement: effect of the alternative treatment (annualise the 8 h delta as 8 h)
    s = bn["HYPEUSDT"]
    alt = R["hypeusdt_gap"] = {}
    if s.missing:
        i = int(np.searchsorted(s.t, s.missing[0]))   # index of the record after the gap
        alt["record"] = fmt_ts(int(s.t[i])); alt["rate"] = s.rate_str[i]
        alt["treated_interval_h"] = float(s.ivl_h[i]); alt["observed_delta_h"] = 8.0
        w = s.ivl_h.copy(); a = s.ann.copy()
        mean_treated = np.average(a, weights=w)
        w2 = w.copy(); a2 = a.copy(); w2[i] = 8.0; a2[i] = s.rate[i] * HOURS_PER_YEAR / 8
        alt["mean_ann_pct_treated"] = float(100 * mean_treated)
        alt["mean_ann_pct_alternative"] = float(100 * np.average(a2, weights=w2))
        alt["cls_treated"] = int(s.cls[i])
        alt["cls_alternative"] = int((s.rate_dec[i] > BASE_PER_HOUR * 8) - (s.rate_dec[i] < BASE_PER_HOUR * 8))

    # venue comparison
    cmp = OrderedDict()
    for c, sym in BN_OF.items():
        r = venue_comparison(hl[c], bn[sym])
        if r:
            cmp[c] = r
    R["venues"] = {c: {"overall": r["overall"], "by_year": r["by_year"]} for c, r in cmp.items()}

    # U1 window (the author's original run)
    W = R["window"] = {"start": fmt_ts(WINDOW_START_MS), "end": fmt_ts(WINDOW_END_MS)}
    W["HL"] = {c: window_stats(hl[c], WINDOW_START_MS, WINDOW_END_MS + 59_999) for c in HL_COINS}
    W["BN"] = {k: window_stats(bn[k], WINDOW_START_MS, WINDOW_END_MS + 59_999) for k in BN_SYMBOLS}
    W["venues"] = {}
    for c, r in cmp.items():
        sr = r["series"]
        m = (sr["t"] >= WINDOW_START_MS) & (sr["t"] <= WINDOW_END_MS + 59_999)
        w = sr["I"][m]
        W["venues"][c] = {"windows": int(m.sum()),
                          "hl_mean_ann_pct": float(100 * np.average(sr["hl_ann"][m], weights=w)),
                          "bn_mean_ann_pct": float(100 * np.average(sr["bn_ann"][m], weights=w)),
                          "diff_hl_minus_bn_pct": float(100 * (np.average(sr["hl_ann"][m], weights=w) - np.average(sr["bn_ann"][m], weights=w))),
                          "corr": float(np.corrcoef(sr["hl_ann"][m], sr["bn_ann"][m])[0, 1])}

    # figures
    fig_base_mass(hl, ys_hl, hist)
    fig_timeseries(hl)
    fig_share_above(ys_hl, ys_bn)
    fig_venues(cmp)
    fig_distribution(ys_hl, ys_bn)

    with open(os.path.join(RES, "analysis.json"), "w") as f:
        json.dump(R, f, indent=1, default=str)
    interpretations(R)
    write_docs(R)
    print("done", file=sys.stderr)



# --------------------------------------------------------------------------- documents

def interpretations(R):
    """Reading of the results. Every number is interpolated from R; the sentences only
    describe what the tables above them show."""
    ys_hl, ys_bn, FH, W, V = R["by_year"]["HL"], R["by_year"]["BN"], R["full_history"], R["window"], R["venues"]
    at_full = {c: FH["HL"][c]["share_at_pct"] for c in HL_COINS}
    lo_c, hi_c = min(at_full, key=at_full.get), max(at_full, key=at_full.get)
    ab26 = {c: ys_hl[c][2026]["share_above_pct"] for c in ("BTC", "ETH", "SOL")}
    ab24 = {c: ys_hl[c][2024]["share_above_pct"] for c in ("BTC", "ETH", "SOL")}
    m24 = {c: ys_hl[c][2024]["mean_ann_pct"] for c in ("BTC", "ETH", "SOL")}
    m26 = {c: ys_hl[c][2026]["mean_ann_pct"] for c in ("BTC", "ETH", "SOL")}
    b21 = {k: ys_bn[k][2021]["mean_ann_pct"] for k in ("BTCUSDT", "ETHUSDT", "SOLUSDT")}
    b22 = {k: ys_bn[k][2022]["mean_ann_pct"] for k in ("BTCUSDT", "ETHUSDT", "SOLUSDT")}
    b24 = {k: ys_bn[k][2024]["mean_ann_pct"] for k in ("BTCUSDT", "ETHUSDT", "SOLUSDT")}
    b26 = {k: ys_bn[k][2026]["mean_ann_pct"] for k in ("BTCUSDT", "ETHUSDT", "SOLUSDT")}
    d = {c: V[c]["overall"]["diff_hl_minus_bn_pct"] for c in ("BTC", "ETH", "SOL")}
    corr = {c: V[c]["overall"]["corr"] for c in ("BTC", "ETH", "SOL")}
    sol22 = ys_bn["SOLUSDT"][2022]
    full_year_medians = [ys_hl[c][y]["median_ann_pct"] for c in HL_COINS for y in ys_hl[c] if not ys_hl[c][y]["partial"]]
    med_sentence = (f"the median annualised rate is {R['base_ann_simple_pct']:.2f} %/yr (the base itself) in all "
                    f"{len(full_year_medians)} full calendar market-years of Hyperliquid"
                    if all(abs(m - R["base_ann_simple_pct"]) < 1e-9 for m in full_year_medians) else
                    f"the median annualised rate equals the base in {sum(abs(m - R['base_ann_simple_pct']) < 1e-9 for m in full_year_medians)} "
                    f"of {len(full_year_medians)} full calendar market-years of Hyperliquid")
    R["interpretation_03"] = f"""## 7. Reading of the results

- **The point mass is the dominant feature.** Over the whole retained history the share of hours settled at
  exactly the base ranges from {at_full[lo_c]:.1f} % ({lo_c}) to {at_full[hi_c]:.1f} % ({hi_c}); {med_sentence} (§3). Means are driven by the two tails, not by the centre.
- **The tails have thinned on the upside.** For BTC/ETH/SOL the share of hours strictly above the base was
  {ab24['BTC']:.1f} % / {ab24['ETH']:.1f} % / {ab24['SOL']:.1f} % in 2024 and is {ab26['BTC']:.1f} % / {ab26['ETH']:.1f} % /
  {ab26['SOL']:.1f} % in 2026 (partial, {ys_hl['BTC'][2026]['days']:.0f} d). Hour-weighted means went from
  {m24['BTC']:.2f} / {m24['ETH']:.2f} / {m24['SOL']:.2f} %/yr to {m26['BTC']:.2f} / {m26['ETH']:.2f} / {m26['SOL']:.2f} %/yr.
  In 2026 the below-base tail dominates: {ys_hl['BTC'][2026]['share_below_pct']:.1f} % (BTC), {ys_hl['ETH'][2026]['share_below_pct']:.1f} % (ETH),
  {ys_hl['SOL'][2026]['share_below_pct']:.1f} % (SOL) of hours.
- **The regime change is visible on Binance, the only venue with pre-2023 data.** BTCUSDT / ETHUSDT / SOLUSDT
  averaged {b21['BTCUSDT']:.2f} / {b21['ETHUSDT']:.2f} / {b21['SOLUSDT']:.2f} %/yr in 2021, {b22['BTCUSDT']:.2f} / {b22['ETHUSDT']:.2f} /
  {b22['SOLUSDT']:.2f} %/yr in 2022, {b24['BTCUSDT']:.2f} / {b24['ETHUSDT']:.2f} / {b24['SOLUSDT']:.2f} %/yr in 2024 and
  {b26['BTCUSDT']:.2f} / {b26['ETHUSDT']:.2f} / {b26['SOLUSDT']:.2f} %/yr in 2026 (partial). The path is not monotonic: 2022 was
  already at or below the 2026 level and 2024 rebounded above the base.
- **Venue.** Over the full overlap Hyperliquid settles higher than Binance on the same market by
  {d['BTC']:+.2f} / {d['ETH']:+.2f} / {d['SOL']:+.2f} pp (BTC / ETH / SOL), with window-level correlations of
  {corr['BTC']:.2f} / {corr['ETH']:.2f} / {corr['SOL']:.2f}: the two venues move together and the decline appears on both
  (§5, by year). The venue is therefore not what makes the recent funding low; if anything Binance is lower.
- **Extreme values are cadence artefacts of annualisation, not errors.** SOLUSDT's 2022 minimum of
  {sol22['min_ann_pct']:.0f} %/yr is the −2 % cap settled at the 2 h cadence of November 2022 (−0.02 × 4,380). Such values
  are why medians and shares are reported alongside means.
"""
    W_HL, W_V = W["HL"], W["venues"]
    diffs = {c: W_HL[c]["mean_ann_pct"] - RECALLED["annual_mean_pct"][c] for c in HL_COINS}
    maxd = max(abs(v) for v in diffs.values())
    R["interpretation_04_window"] = f"""### 1.5 Assessment on the window

- **Annual means:** all five recalled means are reproduced; the largest absolute difference is {maxd:.3f} pp,
  i.e. rounding to two decimals. The recalled figures were computed on the same 8,760 settlements with the same
  convention.
- **Share of hours above the base:** BTC {W_HL['BTC']['share_above_pct']:.2f} % and ETH {W_HL['ETH']['share_above_pct']:.2f} % against
  the recalled ~{RECALLED['share_hours_above_base_pct']['BTC']:.1f} % and ~{RECALLED['share_hours_above_base_pct']['ETH']:.1f} %: reproduced. Note what
  the number means: it is the share *strictly above* the base; a further {W_HL['BTC']['share_at_pct']:.1f} % (BTC) and
  {W_HL['ETH']['share_at_pct']:.1f} % (ETH) of hours sit *exactly at* the base, so "at or above" would be
  {W_HL['BTC']['share_at_pct'] + W_HL['BTC']['share_above_pct']:.1f} % and {W_HL['ETH']['share_at_pct'] + W_HL['ETH']['share_above_pct']:.1f} %.
- **"30–37 % in 2021 → 2–3 % in 2026":** the 2021 leg can only be Binance and holds for BTCUSDT
  ({b21['BTCUSDT']:.2f} %) and ETHUSDT ({b21['ETHUSDT']:.2f} %); SOLUSDT was {b21['SOLUSDT']:.2f} %. The 2026 leg holds for
  BTCUSDT ({b26['BTCUSDT']:.2f} %) but not for ETHUSDT ({b26['ETHUSDT']:.2f} %) or SOLUSDT ({b26['SOLUSDT']:.2f} %), and not on
  Hyperliquid, where 2026 is {m26['BTC']:.2f} / {m26['ETH']:.2f} / {m26['SOL']:.2f} %/yr. Restricted to the window, Binance
  BTCUSDT / ETHUSDT / SOLUSDT average {W['BN']['BTCUSDT']['mean_ann_pct']:.2f} / {W['BN']['ETHUSDT']['mean_ann_pct']:.2f} /
  {W['BN']['SOLUSDT']['mean_ann_pct']:.2f} %/yr. The claim holds as a statement about BTC and ETH on Binance, endpoint to endpoint;
  it does not hold as stated for SOL, for 2026 on ETH, or for Hyperliquid.
- **"The venue difference does not explain the phenomenon":** on the window Hyperliquid is *above* Binance on every
  market (BTC {W_V['BTC']['diff_hl_minus_bn_pct']:+.2f} pp, ETH {W_V['ETH']['diff_hl_minus_bn_pct']:+.2f} pp, SOL
  {W_V['SOL']['diff_hl_minus_bn_pct']:+.2f} pp, HYPE {W_V['HYPE']['diff_hl_minus_bn_pct']:+.2f} pp) and both venues are far below
  their 2021/2024 levels, so low funding is not a Hyperliquid-specific artefact. The claim holds, with the
  quantified caveat that the venues are not interchangeable: a systematic Hyperliquid premium exists.
"""
    R["interpretation_04_full"] = f"""| Claim | On the one-year window | On the full history |
|---|---|---|
| Annual means BTC {RECALLED['annual_mean_pct']['BTC']:.2f} / ETH {RECALLED['annual_mean_pct']['ETH']:.2f} / SOL {RECALLED['annual_mean_pct']['SOL']:.2f} / HYPE {RECALLED['annual_mean_pct']['HYPE']:.2f} / PURR {RECALLED['annual_mean_pct']['PURR']:.2f} %/yr | Reproduced ({', '.join(f"{c} {W_HL[c]['mean_ann_pct']:.2f}" for c in HL_COINS)}) | Window-specific. Whole-history hour-weighted means: {', '.join(f"{c} {FH['HL'][c]['mean_ann_pct']:.2f}" for c in HL_COINS)} %/yr. |
| BTC above base ~{RECALLED['share_hours_above_base_pct']['BTC']:.1f} % of hours, ETH ~{RECALLED['share_hours_above_base_pct']['ETH']:.1f} % | Reproduced ({W_HL['BTC']['share_above_pct']:.2f} % / {W_HL['ETH']['share_above_pct']:.2f} %) | Holds only for the last year. Whole history: BTC {FH['HL']['BTC']['share_above_pct']:.1f} %, ETH {FH['HL']['ETH']['share_above_pct']:.1f} %; 2024: {ab24['BTC']:.1f} % / {ab24['ETH']:.1f} %; 2026 (partial): {ab26['BTC']:.1f} % / {ab26['ETH']:.1f} %. It is a property of the current regime, not of the markets. |
| Funding fell from 30–37 % (2021) to 2–3 % (2026) | 2026 leg on the window: Binance BTCUSDT {W['BN']['BTCUSDT']['mean_ann_pct']:.2f} %, ETHUSDT {W['BN']['ETHUSDT']['mean_ann_pct']:.2f} %, SOLUSDT {W['BN']['SOLUSDT']['mean_ann_pct']:.2f} % | Holds endpoint-to-endpoint for BTCUSDT ({b21['BTCUSDT']:.2f} → {b26['BTCUSDT']:.2f}) and, with a 2026 value below the stated range, ETHUSDT ({b21['ETHUSDT']:.2f} → {b26['ETHUSDT']:.2f}); not for SOLUSDT ({b21['SOLUSDT']:.2f} → {b26['SOLUSDT']:.2f}). It hides that 2022 ({b22['BTCUSDT']:.2f} / {b22['ETHUSDT']:.2f} / {b22['SOLUSDT']:.2f}) was already low and 2024 ({b24['BTCUSDT']:.2f} / {b24['ETHUSDT']:.2f} / {b24['SOLUSDT']:.2f}) rebounded. Hyperliquid shows the same 2024 → 2026 fall ({m24['BTC']:.2f} → {m26['BTC']:.2f} BTC). |
| Venue difference does not explain it | Holds: HL − Binance {W_V['BTC']['diff_hl_minus_bn_pct']:+.2f} / {W_V['ETH']['diff_hl_minus_bn_pct']:+.2f} / {W_V['SOL']['diff_hl_minus_bn_pct']:+.2f} pp (BTC/ETH/SOL), both venues low | Holds: HL − Binance {d['BTC']:+.2f} / {d['ETH']:+.2f} / {d['SOL']:+.2f} pp over the full overlap, correlation {corr['BTC']:.2f} / {corr['ETH']:.2f} / {corr['SOL']:.2f}; the decline is on both venues, and Hyperliquid carries a persistent premium over Binance. |

Nothing was adjusted to approach the recalled figures; the recomputed values are the published ones.
"""


def f2(x):
    return f"{x:.2f}"


def f1(x):
    return f"{x:.1f}"


def pct_share(st):
    return f"{st['share_at_pct']:.1f} % / {st['share_above_pct']:.1f} % / {st['share_below_pct']:.1f} %"


def ylab(y, st):
    return f"{y}* ({st['days']:.0f} d)" if st["partial"] else f"{y}"


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def load_verify():
    path = os.path.join(RES, "verify-full-vs-baseline.json")
    with open(path) as f:
        return json.load(f)


def write_docs(R):
    inv, ys_hl, ys_bn = R["inventory"], R["by_year"]["HL"], R["by_year"]["BN"]
    base_pct, comp_pct = R["base_ann_simple_pct"], R["base_ann_compound_pct"]
    ver = load_verify()
    today = R["generated_utc"][:10]

    # ---------------- 03-analysis.md
    L = []
    L.append(f"# U3 — Analysis of the funding-rate series\n")
    L.append(f"Generated {R['generated_utc']} by `scripts/analyse.py` from `data/full/`. Every number in this "
             "document and in the figures is computed by that script; none is typed by hand. "
             "Re-running the script regenerates this file, `docs/04-discrepancies.md`, `figures/` and "
             "`results/analysis.json`.\n")
    L.append("## 0. Dataset: `data/full/`\n")
    L.append("Downloaded with the U2 downloader, full retained history on both venues, frozen and hashed "
             "(`data/full/SHA256SUMS`):\n\n```\npython3 scripts/download.py --out data/full "
             "--hl-start 2023-01-01T00:00:00Z --end 2026-09-14T00:00:00Z\n```\n\n"
             "Binance is downloaded from its first record (`startTime=1`, the default). The Hyperliquid API "
             "returns from the start of its retained history regardless of the earlier `--hl-start`. The "
             "explicit `--end` makes the freeze reproducible (a re-run with the same arguments must hash "
             "identically unless a venue rewrites history). `data/baseline/` (U1) is untouched.\n")
    rows = []
    for k, v in inv.items():
        rows.append([("Hyperliquid " if v["venue"] == "HL" else "Binance ") + v["market"], f"{v['records']:,}",
                     v["first"], v["last"], f"{v['hours_covered']:,.0f}", f"{v['hours_covered']/24:,.1f}",
                     ", ".join(str(y) for y in v["years"])])
    L.append(md_table(["Series", "Records", "First (UTC)", "Last (UTC)", "Hours covered", "Days", "Calendar years"], rows) + "\n")

    L.append("### 0.1 Comparison against `data/baseline/`\n")
    L.append("`python3 scripts/verify.py --downloaded data/full --json results/verify-full-vs-baseline.json` "
             "(same key and equality definition as docs/02-download.md §7):\n")
    rows = [[r["series"], f"{r['baseline_records']:,}", f"{r['downloaded_records']:,}", f"{r['identical']:,}",
             f"{r['differ']:,}", f"{r['only_baseline']:,}",
             f"{r['only_downloaded']:,} ({r['only_downloaded_before_span']:,} / {r['only_downloaded_inside_span']:,} / {r['only_downloaded_after_span']:,})"]
            for r in ver]
    L.append(md_table(["Series", "Baseline", "data/full", "Identical", "Differ in value", "Only in baseline",
                       "Only in data/full (before / inside / after baseline span)"], rows) + "\n")
    ok = all(r["differ"] == 0 and r["only_baseline"] == 0 and r["only_downloaded_inside_span"] == 0 for r in ver)
    tot_ident = sum(r["identical"] for r in ver); tot_base = sum(r["baseline_records"] for r in ver)
    L.append((f"Result: {tot_ident:,} of {tot_base:,} baseline records reappear identical in `data/full/`; "
              f"{sum(r['differ'] for r in ver)} differ in value, {sum(r['only_baseline'] for r in ver)} are only in the "
              f"baseline, {sum(r['only_downloaded_inside_span'] for r in ver)} are only in `data/full/` inside the baseline "
              f"span. " + ("The extended dataset is a strict superset of the baseline; the analysis proceeds." if ok
                           else "**A baseline record does not reappear identical: STOP and report (see the rows above).**")) + "\n")

    L.append("### 0.2 Settlement cadence observed in `data/full/` and how each run is treated\n")
    rows = []
    for k, v in inv.items():
        for r in v["runs"]:
            treat = "cadence run" if r["treated_as"] == "cadence run" else f"omitted settlement(s); record annualised at {r['cadence_h']:g} h"
            rows.append([v["market"] + (" (HL)" if v["venue"] == "HL" else " (Binance)"), f"{r['interval_h']:g} h", r["from_utc"], r["to_utc"], f"{r['deltas']:,}", treat])
    L.append(md_table(["Series", "Delta", "From (UTC)", "To (UTC)", "Deltas", "Treatment"], rows) + "\n")
    om = [(v["market"], v["venue"], m) for v in inv.values() for m in v["missing"]]
    L.append("Omitted settlements (a single delta that is a whole multiple of the cadence on both sides of it): " +
             (", ".join(f"{mk} ({'HL' if ve == 'HL' else 'Binance'}) {m}" for mk, ve, m in om) if om else "none") + ".\n")
    ev = OrderedDict()
    for v in inv.values():
        for d in v["delayed"]:
            if d["delta_min"] > round(d["delta_min"] / 60) * 60:      # the late settlement itself (long delta)
                ev.setdefault((d["to_exact"], round(d["delta_min"], 1)), []).append(v["market"] + ("" if v["venue"] == "HL" else " (Binance)"))
    L.append("Settlements executed minutes late (the next settlement then fell on the regular hour, so the two deltas "
             "sum to the cadence; both are rounded to the cadence). Each event affects every market listed, i.e. it is "
             "venue-wide: " + ("; ".join(f"{k[0]} UTC, {k[1]:.1f} min after the previous settlement ({', '.join(m)})"
                               for k, m in ev.items()) if ev else "none") + ".\n")
    max_jit = max(v["max_jitter_ms"] for v in inv.values())
    max_jit_hl = max(v["max_jitter_ms"] for v in inv.values() if v["venue"] == "HL")
    max_jit_bn = max(v["max_jitter_ms"] for v in inv.values() if v["venue"] == "BN")

    L.append("## 1. Calculation rules\n")
    L.append(f"""1. **Annualisation** is the simple convention fixed in docs/01-data-audit.md §7: per-settlement rate ×
   (8,760 h / interval in hours). It is applied identically to the observed funding and to the base rate.
   The Hyperliquid base component is {R['base_per_hour']} per hour, i.e. **{base_pct:.2f} %/yr** under this
   convention (the compound figure would be {comp_pct:.2f} %/yr; it is not used anywhere below).
   Binance's interest-rate component is 0.0001 per 8 h, the same value per hour, so one base line serves both venues.
2. **Settlements per year** are derived from the observed interval between consecutive timestamps, rounded to
   the nearest hour, never assumed: 8,760/yr for 1 h, 4,380/yr for 2 h, 2,190/yr for 4 h, 1,095/yr for 8 h. The
   SOLUSDT runs of November 2022 at 4 h and 2 h are annualised with their real interval, and so is
   Hyperliquid's own 8 h regime of May–June 2023 (§0.2), which the extended download revealed.
3. **Omitted settlements.** A single delta that is a whole multiple of the cadence on both sides of it is a missing
   settlement, not a cadence change. The record that follows it keeps the cadence of its run for annualisation
   and for the hour weight; the omitted slot is simply absent from every count (no imputation). This covers
   HYPEUSDT 2026-06-24 04:00 on Binance and the Hyperliquid slots listed in §0.2. For HYPEUSDT the 08:00 rate
   ({R['hypeusdt_gap'].get('rate')}) is annualised as a 4 h rate; whether it accrued 4 h or 8 h is unknown. Under the
   alternative (annualise it as an 8 h rate) the HYPEUSDT full-history mean moves from
   {R['hypeusdt_gap'].get('mean_ann_pct_treated', float('nan')):.4f} %/yr to {R['hypeusdt_gap'].get('mean_ann_pct_alternative', float('nan')):.4f} %/yr, and that one
   record is classified "{ {1: 'above', 0: 'at', -1: 'below'}.get(R['hypeusdt_gap'].get('cls_treated')) }" base as a 4 h rate versus
   "{ {1: 'above', 0: 'at', -1: 'below'}.get(R['hypeusdt_gap'].get('cls_alternative')) }" base as an 8 h rate: one settlement of
   {R['inventory']['BN:HYPEUSDT']['records']:,}.
4. **Delayed settlements** (a settlement minutes late, the next one back on the hour) are rounded to the cadence;
   they are listed in §0.2. Apart from those, the largest departure of a timestamp from its rounded hour is
   {max_jit_hl/1000:.1f} s on Hyperliquid and {max_jit_bn/1000:.3f} s on Binance; rounding to the hour is therefore
   unambiguous.
5. **Base classification** is an exact decimal comparison of the API string against the base per settlement
   ({R['base_per_hour']} × interval hours), with no rounding and no float. Above/at/below counts are reported
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
""")

    L.append("## 2. Main result: the funding distribution is a point mass at the base with two tails\n")
    L.append(f"Mechanically, F = P + clamp(r − P, −0.0005, 0.0005) equals r exactly whenever |r − P| ≤ 0.0005, so every "
             f"hour whose average premium lies within ±0.05 % of the base settles at exactly {R['base_per_hour']}/h. "
             "Shares of settlement-hours exactly at / strictly above / strictly below the base, per market and calendar "
             "year (Hyperliquid, exact decimal comparison, hour-weighted; * partial year with days covered):\n")
    rows = []
    for c in HL_COINS:
        for y, st in ys_hl[c].items():
            rows.append([c, ylab(y, st), f"{st['records']:,}", f"{st['share_at_pct']:.1f} %", f"{st['share_above_pct']:.1f} %",
                         f"{st['share_below_pct']:.1f} %", f"{st['n_at']:,} / {st['n_above']:,} / {st['n_below']:,}"])
    L.append(md_table(["Market", "Year", "Settlements", "Exactly at base", "Above", "Below", "Settlements at / above / below"], rows) + "\n")
    rows = []
    for c in HL_COINS:
        st = R["full_history"]["HL"][c]
        rows.append([c, f"{st['first']} → {st['last']}", f"{st['records']:,}", f"{st['share_at_pct']:.1f} %",
                     f"{st['share_above_pct']:.1f} %", f"{st['share_below_pct']:.1f} %"])
    L.append("Whole retained history per market:\n\n" + md_table(["Market", "Span (UTC)", "Settlements", "Exactly at base", "Above", "Below"], rows) + "\n")
    L.append("![Base mass](../figures/fig0-base-mass.png)\n\n*Figure 0 — top: hour-weighted share at / above / below the base "
             "per market-year; bottom: histogram of the annualised hourly rate per market "
             f"({R['histogram']['BTC']['bin_width_pct']:g} pp bins, log scale), grey bar = the bin containing the base.*\n")

    L.append("### 2.1 Invariance of the classification to the annualisation convention\n")
    L.append("Counts of settlements above / at / below the base over the whole history, computed four ways: exact "
             "decimal strings; float per-settlement rates; float simple-annualised rates vs. the simple-annualised "
             "base; float compound-annualised rates vs. the compound-annualised base. Since annualising is a strictly "
             "increasing transformation applied to both sides, the ordering cannot change; the table verifies it holds "
             "numerically too:\n")
    rows = []
    for venue, names in (("HL", HL_COINS), ("BN", BN_SYMBOLS)):
        for n in names:
            iv = R["invariance"][venue][n]
            cell = lambda k: f"{iv[k]['above']:,} / {iv[k]['at']:,} / {iv[k]['below']:,}"
            rows.append([("Hyperliquid " if venue == "HL" else "Binance ") + n, f"{iv['records']:,}", cell("exact_decimal"), cell("float_raw"),
                         cell("float_simple_annualised"), cell("float_compound_annualised"), "yes" if iv["all_identical"] else "**NO**"])
    L.append(md_table(["Series", "Records", "Exact decimal", "Float raw", "Simple annualised", "Compound annualised", "Identical"], rows) + "\n")
    inv_ok = all(R["invariance"][v][n]["all_identical"] for v, ns in (("HL", HL_COINS), ("BN", BN_SYMBOLS)) for n in ns)
    L.append(("All four counts coincide for every series: the classification is invariant to the annualisation convention.\n"
              if inv_ok else "**The counts do not coincide for at least one series; see the table.**\n"))

    L.append("## 3. Annualised funding over time, with the base rate\n")
    L.append("![Time series](../figures/fig1-timeseries-annualised.png)\n\n*Figure 1 — simple-annualised Hyperliquid funding, "
             "hour-weighted trailing means over 30 days (thick) and 7 days (thin); dashed line = base "
             f"{base_pct:.2f} %/yr.*\n")
    rows = []
    for c in HL_COINS:
        for y, st in ys_hl[c].items():
            rows.append([c, ylab(y, st), f"{st['mean_ann_pct']:.2f}", f"{st['median_ann_pct']:.2f}", f"{st['q05_ann_pct']:.1f}",
                         f"{st['q25_ann_pct']:.2f}", f"{st['q75_ann_pct']:.2f}", f"{st['q95_ann_pct']:.1f}", f"{st['min_ann_pct']:.0f}", f"{st['max_ann_pct']:.0f}"])
    L.append("Per calendar year, %/yr (hour-weighted mean; per-settlement median and quantiles):\n\n" +
             md_table(["Market", "Year", "Mean", "Median", "p5", "p25", "p75", "p95", "Min", "Max"], rows) + "\n")

    L.append("## 4. Share of hours per year above the base\n")
    L.append("![Share above base](../figures/fig2-share-above-base.png)\n\n*Figure 2 — hour-weighted share of each "
             "calendar year in which funding was strictly above the venue base (Hyperliquid left, Binance right, same "
             "base per hour on both).*\n")
    years = sorted({y for ys in list(ys_hl.values()) + list(ys_bn.values()) for y in ys})
    header = ["Year"] + [f"HL {c}" for c in HL_COINS] + [f"BN {s}" for s in BN_SYMBOLS]
    rows = []
    for y in years:
        cells = []
        for c in HL_COINS:
            st = ys_hl[c].get(y); cells.append(f"{st['share_above_pct']:.1f} %" + ("*" if st["partial"] else "") if st else "—")
        for sname in BN_SYMBOLS:
            st = ys_bn[sname].get(y); cells.append(f"{st['share_above_pct']:.1f} %" + ("*" if st["partial"] else "") if st else "—")
        rows.append([str(y)] + cells)
    L.append(md_table(header, rows) + "\n")
    part = []
    for venue, ys_all in (("HL", ys_hl), ("BN", ys_bn)):
        for n, ys in ys_all.items():
            for y, st in ys.items():
                if st["partial"]:
                    part.append(f"{n} {y}: {st['days']:.0f} d ({st['first']} → {st['last']})")
    L.append("\\* partial years: " + "; ".join(part) + ".\n")
    rows = []
    for sname in BN_SYMBOLS:
        for y, st in ys_bn[sname].items():
            rows.append([sname, ylab(y, st), f"{st['records']:,}", f"{st['share_at_pct']:.1f} %", f"{st['share_above_pct']:.1f} %", f"{st['share_below_pct']:.1f} %",
                         f"{st['mean_ann_pct']:.2f}", f"{st['median_ann_pct']:.2f}"])
    L.append("Binance per year, for reference (same layout as §2, plus mean and median in %/yr):\n\n" +
             md_table(["Symbol", "Year", "Settlements", "Exactly at base", "Above", "Below", "Mean", "Median"], rows) + "\n")

    L.append("## 5. Hyperliquid vs. Binance on the same market and period\n")
    L.append("![Venues](../figures/fig3-venue-comparison.png)\n\n*Figure 3 — 30-day trailing means of the annualised rate per "
             "Binance settlement window, Hyperliquid hourly rates summed into the same windows.*\n")
    rows = []
    for c, r in R["venues"].items():
        o = r["overall"]
        rows.append([c, f"{o['first']} → {o['last']}", f"{o['windows']:,}", f"{o['hl_mean_ann_pct']:.2f}", f"{o['bn_mean_ann_pct']:.2f}",
                     f"{o['diff_hl_minus_bn_pct']:+.2f}", f"{o['mean_abs_diff_pct']:.2f}", f"{o['corr']:.3f}", f"{o['share_windows_hl_above_bn_pct']:.1f} %"])
    L.append(md_table(["Market", "Overlap (UTC)", "Windows", "HL mean %/yr", "Binance mean %/yr", "HL − Binance (pp)",
                       "Mean abs. diff (pp)", "Corr.", "Windows HL > Binance"], rows) + "\n")
    rows = []
    for c, r in R["venues"].items():
        for y, o in r["by_year"].items():
            rows.append([c, f"{y}" + ("*" if o["days"] < 364 else "") + f" ({o['days']:.0f} d)", f"{o['windows']:,}", f"{o['hl_mean_ann_pct']:.2f}", f"{o['bn_mean_ann_pct']:.2f}",
                         f"{o['diff_hl_minus_bn_pct']:+.2f}", f"{o['corr']:.3f}"])
    L.append("By calendar year (days = overlap days in that year; * partial):\n\n" +
             md_table(["Market", "Year", "Windows", "HL mean %/yr", "Binance mean %/yr", "HL − Binance (pp)", "Corr."], rows) + "\n")

    L.append("## 6. Distribution by year: the regime change\n")
    L.append("![Distribution](../figures/fig4-distribution-by-year.png)\n\n*Figure 4 — per-settlement annualised rate by "
             "calendar year: p5–p95, p25–p75, median, hour-weighted mean; dashed = base.*\n")
    rows = []
    for sname in BN_SYMBOLS:
        for y, st in ys_bn[sname].items():
            rows.append([sname, ylab(y, st), f"{st['mean_ann_pct']:.2f}", f"{st['median_ann_pct']:.2f}", f"{st['q05_ann_pct']:.1f}",
                         f"{st['q25_ann_pct']:.2f}", f"{st['q75_ann_pct']:.2f}", f"{st['q95_ann_pct']:.1f}", f"{st['min_ann_pct']:.0f}", f"{st['max_ann_pct']:.0f}"])
    L.append("Binance per calendar year, %/yr:\n\n" + md_table(["Symbol", "Year", "Mean", "Median", "p5", "p25", "p75", "p95", "Min", "Max"], rows) + "\n")
    L.append(R.get("interpretation_03", ""))
    with open(os.path.join(DOCS, "03-analysis.md"), "w") as f:
        f.write("\n".join(L))

    # ---------------- 04-discrepancies.md
    W = R["window"]
    D = []
    D.append("# U3 — Discrepancies: recalled figures vs. recomputation\n")
    D.append(f"Generated {R['generated_utc']} by `scripts/analyse.py`. The recalled figures come from the author's "
             f"original run over the window {W['start']} → {W['end']} UTC (8,760 hourly Hyperliquid settlements, simple "
             "annualisation). They are a checklist, not a target: nothing in the calculation was adjusted to approach "
             "them. §1 recomputes each figure on exactly that window from `data/full/`; §2 asks whether each claim holds "
             "on the full history.\n")
    D.append("## 1. Same window, same convention\n")
    D.append("### 1.1 Annual means (simple annualisation, %/yr)\n")
    rows = []
    for c in HL_COINS:
        rec = RECALLED["annual_mean_pct"][c]; st = W["HL"][c]
        rows.append([c, f"{st['records']:,}", f"{rec:.2f}", f"{st['mean_ann_pct']:.4f}", f"{st['mean_ann_pct'] - rec:+.4f}"])
    D.append(md_table(["Market", "Settlements in window", "Recalled", "Recomputed", "Difference (pp)"], rows) + "\n")
    D.append("### 1.2 Share of hours above the base\n")
    rows = []
    for c in ("BTC", "ETH"):
        rec = RECALLED["share_hours_above_base_pct"][c]; st = W["HL"][c]
        rows.append([c, f"~{rec:.1f} %", f"{st['share_above_pct']:.2f} % ({st['n_above']:,} of {st['records']:,} h)", f"{st['share_above_pct'] - rec:+.2f} pp",
                     f"{st['share_at_pct']:.2f} %", f"{st['share_below_pct']:.2f} %"])
    D.append(md_table(["Market", "Recalled", "Recomputed (strictly above)", "Difference", "Exactly at base", "Below"], rows) + "\n")
    rows = []
    for c in HL_COINS:
        st = W["HL"][c]
        rows.append([c, f"{st['share_above_pct']:.2f} %", f"{st['share_at_pct']:.2f} %", f"{st['share_below_pct']:.2f} %", f"{st['median_ann_pct']:.2f}"])
    D.append("All five markets in the window, for completeness:\n\n" + md_table(["Market", "Above", "At base", "Below", "Median %/yr"], rows) + "\n")
    D.append("### 1.3 \"Funding fell from 30–37 % annualised in 2021 to 2–3 % in 2026\"\n")
    r21 = RECALLED["regime_2021_pct"]; r26 = RECALLED["regime_2026_pct"]
    rows = []
    for sname in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        st21 = ys_bn[sname].get(2021); st26 = ys_bn[sname].get(2026)
        rows.append([f"Binance {sname}", ylab(2021, st21) if st21 else "—", f"{st21['mean_ann_pct']:.2f}" if st21 else "—",
                     ylab(2026, st26), f"{st26['mean_ann_pct']:.2f}", f"{st26['median_ann_pct']:.2f}"])
    for c in HL_COINS:
        st26 = ys_hl[c].get(2026)
        rows.append([f"Hyperliquid {c}", "—", "—", ylab(2026, st26), f"{st26['mean_ann_pct']:.2f}", f"{st26['median_ann_pct']:.2f}"])
    D.append(f"Recalled: {r21[0]:.0f}–{r21[1]:.0f} %/yr in 2021 and {r26[0]:.0f}–{r26[1]:.0f} %/yr in 2026. Hyperliquid has no 2021 data, "
             "so the 2021 figure can only refer to Binance. Hour-weighted means per calendar year, %/yr:\n\n" +
             md_table(["Series", "2021", "Mean 2021", "2026", "Mean 2026", "Median 2026"], rows) + "\n")
    D.append("### 1.4 \"The difference between venues does not explain the phenomenon\"\n")
    rows = []
    for c, o in W["venues"].items():
        rows.append([c, f"{o['windows']:,}", f"{o['hl_mean_ann_pct']:.2f}", f"{o['bn_mean_ann_pct']:.2f}", f"{o['diff_hl_minus_bn_pct']:+.2f}", f"{o['corr']:.3f}"])
    D.append("Same window, Hyperliquid hourly rates summed into the Binance settlement windows, %/yr:\n\n" +
             md_table(["Market", "Windows", "HL mean", "Binance mean", "HL − Binance (pp)", "Corr."], rows) + "\n")
    D.append(R.get("interpretation_04_window", ""))
    D.append("## 2. Does each claim hold on the full history?\n")
    D.append(R.get("interpretation_04_full", ""))
    with open(os.path.join(DOCS, "04-discrepancies.md"), "w") as f:
        f.write("\n".join(D))


if __name__ == "__main__":
    main()
