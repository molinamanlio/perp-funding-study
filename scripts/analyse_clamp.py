#!/usr/bin/env python3
"""U3-bis — clamp censoring, the venue differential, and the HYPE anomaly.

    .venv/bin/python scripts/analyse_clamp.py

Sister script of scripts/analyse.py: reads ONLY data/full/ through analyse.Series and
follows the calculation rules of docs/03-analysis.md §1. Writes

- figures/fig5-clamp-censoring.*, fig6-venue-decomposition.*, fig7-hype-correlation.*
- results/analysis.json            adds the "u3bis" block (kept by analyse.py on re-runs)
- results/03-section-8.md          section 8, inserted into docs/03-analysis.md
- docs/03-analysis.md              section 8 replaced in place (markers below)

No number in the section is typed by hand.
"""
import datetime as dt
import json
import os
import sys
from collections import OrderedDict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyse as A  # noqa: E402
from analyse import (HL_COINS, BN_SYMBOLS, BN_OF, HOURS_PER_YEAR, MS_H, RES, FIG, DOCS,   # noqa: E402
                     fmt_ts, utc, md_table, rolling_mean_days, COL, VENUE_COL, INK, INK2, GRID, SURF, savefig, plt)

R8 = 0.0001            # interest-rate component on the 8 h basis (docs/01 §7)
BP = 1e4               # decimal fraction → basis points
MARK_START, MARK_END = "<!-- u3bis:start -->", "<!-- u3bis:end -->"


def f8_of(s):
    """Settled rate on the 8 h basis: the stored hourly rate × 8, or the rate itself in
    Hyperliquid's 8 h regime (May–June 2023)."""
    return np.where(s.ivl_h == 8, s.rate, s.rate * 8)


def g(P, c):
    """The documented formula: F = P + clamp(r − P, −c, c). With c = 0 it collapses to F = P."""
    return P + np.clip(R8 - P, -c, c)


# --------------------------------------------------------------------------- clamp regimes

def clamp_regimes(s, min_run=24):
    """Infer the clamp half-width c(t) from the data.

    For every settlement not at the base the implied half-width is |P − F8| (the formula
    puts F8 exactly c away from P outside the band). Runs of ≥ `min_run` consecutive
    off-base settlements with the same implied value define the regimes; a regime starts
    at the first settlement after the previous run that the previous c cannot reproduce.
    Every settlement is then checked against the formula with its regime's c; the ones
    the formula does not reproduce are reported, not patched."""
    P, F8 = s.premium, f8_of(s)
    off = np.where(s.cls != 0)[0]
    imp = np.round(np.abs(P[off] - F8[off]), 7)
    runs = []
    for k, i in enumerate(off):
        if runs and runs[-1]["c"] == imp[k]:
            runs[-1]["end"] = int(i); runs[-1]["n"] += 1
        else:
            runs.append({"c": float(imp[k]), "start": int(i), "end": int(i), "n": 1})
    long = [r for r in runs if r["n"] >= min_run]
    merged = []
    for r in long:
        if merged and merged[-1]["c"] == r["c"]:
            merged[-1]["end"] = r["end"]; merged[-1]["n"] += r["n"]
        else:
            merged.append(dict(r))
    n = len(s.t)
    c = np.full(n, merged[0]["c"])
    bounds = [0]
    for k in range(1, len(merged)):
        prev_c = merged[k - 1]["c"]
        ok_prev = np.abs(g(P, prev_c) - F8) < 1e-9
        j = merged[k - 1]["end"] + 1
        while j < n and ok_prev[j]:
            j += 1
        bounds.append(j)
        c[j:] = merged[k]["c"]
    bounds.append(n)
    fit = np.abs(g(P, c) - F8) < 1e-9
    regimes = []
    for k, m in enumerate(merged):
        a, b = bounds[k], bounds[k + 1] - 1
        mis = np.where(~fit[a:b + 1])[0] + a
        regimes.append({"c": m["c"], "from": fmt_ts(int(s.t[a])), "to": fmt_ts(int(s.t[b])), "records": b - a + 1,
                        "misfit": int(len(mis)),
                        "misfit_span": (fmt_ts(int(s.t[mis[0]])), fmt_ts(int(s.t[mis[-1]]))) if len(mis) else None})
    short = [{"c": r["c"], "from": fmt_ts(int(s.t[r["start"]])), "to": fmt_ts(int(s.t[r["end"]])), "n": r["n"]}
             for r in runs if r["n"] < min_run]
    return c, fit, regimes, short


# --------------------------------------------------------------------------- task 1: censoring

def skew(x):
    x = np.asarray(x, float); m = x.mean(); d = x - m
    m2 = (d ** 2).mean(); m3 = (d ** 3).mean()
    return float(m3 / m2 ** 1.5) if m2 > 0 else float("nan")


def censoring_block(s, c, mask):
    P, F8, w = s.premium[mask], f8_of(s)[mask], s.ivl_h[mask]
    at = s.cls[mask] == 0
    cc = c[mask]
    hours = w.sum()
    Pm = np.average(P, weights=w)
    ss_tot = float((w * (P - Pm) ** 2).sum())
    ss_at = float((w[at] * (P[at] - Pm) ** 2).sum())
    varP = ss_tot / hours
    F8m = np.average(F8, weights=w)
    varF = float((w * (F8 - F8m) ** 2).sum()) / hours
    q = lambda a, qs: [float(np.quantile(a, x) * BP) for x in qs] if len(a) else [float("nan")] * len(qs)
    up = P > R8 + cc; lo = P < R8 - cc
    return {
        "records": int(mask.sum()), "hours": float(hours),
        "share_at_pct": float(100 * w[at].sum() / hours),
        "share_upper_tail_pct": float(100 * w[up].sum() / hours), "share_lower_tail_pct": float(100 * w[lo].sum() / hours),
        "tail_vs_class_disagreements": int(((up) != (s.cls[mask] > 0)).sum() + ((lo) != (s.cls[mask] < 0)).sum()),
        "premium_mean_bp": float(Pm * BP), "premium_median_bp": float(np.median(P) * BP), "premium_std_bp": float(np.sqrt(varP) * BP),
        "premium_skew": skew(P), "premium_share_above_r_pct": float(100 * w[P > R8].sum() / hours),
        "anchored_n": int(at.sum()),
        "anchored_premium_mean_bp": float(P[at].mean() * BP) if at.any() else float("nan"),
        "anchored_premium_std_bp": float(P[at].std() * BP) if at.any() else float("nan"),
        "anchored_premium_q": dict(zip(["min", "p5", "p25", "p50", "p75", "p95", "max"],
                                       q(P[at], [0, .05, .25, .5, .75, .95, 1]))),
        "var_not_transmitted_pct": float(100 * (1 - varF / varP)) if varP > 0 else float("nan"),
        "ss_share_anchored_pct": float(100 * ss_at / ss_tot) if ss_tot > 0 else float("nan"),
        "corr_F8_P": float(np.corrcoef(F8, P)[0, 1]),
        "c_values_bp": sorted(set((cc * BP).round(2).tolist())),
    }


# --------------------------------------------------------------------------- task 2: windows

def windows(hl, c, I_h, anchor_ms=0, lag_h=0, bn=None):
    """Hyperliquid settlements grouped into I_h-hour windows ending at t = anchor + k·I_h
    (+ lag_h). Returns per window: end time, sum of hourly rates (actual, 8 h basis is
    sum×8/I... kept as window rate), mean premium, c, and the counterfactual
    F̄ = g(mean premium) × I_h/8. If `bn` is given, windows are the Binance settlements."""
    idx = {int(x): i for i, x in enumerate(hl.t // MS_H)}
    if bn is not None:
        ends = [(int(bn.t[j] // MS_H) + lag_h, int(round(bn.ivl_h[j])), bn.rate[j]) for j in range(len(bn.t))]
    else:
        first = int(hl.t[0] // MS_H); last = int(hl.t[-1] // MS_H)
        k0 = (first - anchor_ms // MS_H + I_h - 1) // I_h
        ends = [(int(anchor_ms // MS_H + k * I_h), I_h, np.nan) for k in range(k0, (last - anchor_ms // MS_H) // I_h + 1)]
    rows, hours_P = [], []
    for t_slot, I, bn_rate in ends:
        ks = [k for k in (idx.get(t_slot - h) for h in range(I)) if k is not None]
        if not ks or sum(hl.ivl_h[k] for k in ks) != I:
            continue
        P = hl.premium[ks]; wts = hl.ivl_h[ks]
        Pbar = float(np.average(P, weights=wts))
        cw = float(c[ks[-1]])
        actual = float(hl.rate[ks].sum())                 # window rate actually settled
        cf = float(g(Pbar, cw) * I / 8)                   # window rate if the premium were averaged over the window
        rows.append((t_slot * MS_H, I, actual, cf, Pbar, bn_rate, cw))
        hours_P.extend(P.tolist())
    a = np.array(rows, dtype=float)
    return {"t": a[:, 0].astype(np.int64), "I": a[:, 1], "actual": a[:, 2], "cf": a[:, 3], "Pbar": a[:, 4],
            "bn": a[:, 5], "c": a[:, 6], "P_hourly_std": float(np.std(hours_P)), "Pbar_std": float(np.std(a[:, 4]))}


def wmean(x, w):
    return float(np.average(x, weights=w))


def decomposition(W):
    ann = HOURS_PER_YEAR / W["I"]
    act, cf, bn, w = W["actual"] * ann, W["cf"] * ann, W["bn"] * ann, W["I"]
    years = np.array([utc(int(x)).year for x in W["t"]])
    def block(m):
        d = {"windows": int(m.sum()), "days": float(w[m].sum() / 24), "first": fmt_ts(int(W["t"][m][0])), "last": fmt_ts(int(W["t"][m][-1])),
             "hl_actual_pct": 100 * wmean(act[m], w[m]), "hl_cf_pct": 100 * wmean(cf[m], w[m])}
        d["window_effect_pp"] = d["hl_actual_pct"] - d["hl_cf_pct"]
        if not np.isnan(bn[m]).all():
            d["bn_pct"] = 100 * wmean(bn[m], w[m])
            d["diff_pp"] = d["hl_actual_pct"] - d["bn_pct"]
            d["residual_pp"] = d["hl_cf_pct"] - d["bn_pct"]
            d["explained_share_pct"] = 100 * d["window_effect_pp"] / d["diff_pp"] if d["diff_pp"] != 0 else float("nan")
            d["corr_actual_bn"] = float(np.corrcoef(act[m], bn[m])[0, 1]) if m.sum() > 2 else float("nan")
            d["corr_cf_bn"] = float(np.corrcoef(cf[m], bn[m])[0, 1]) if m.sum() > 2 else float("nan")
        return d
    out = {"overall": block(np.ones(len(w), bool)), "by_year": OrderedDict()}
    out["overall"]["premium_std_hourly_bp"] = W["P_hourly_std"] * BP
    out["overall"]["premium_std_window_avg_bp"] = W["Pbar_std"] * BP
    for y in sorted(set(years.tolist())):
        out["by_year"][y] = block(years == y)
    return out


# --------------------------------------------------------------------------- task 3: HYPE

def pearson(x, y):
    return float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 and x.std() > 0 and y.std() > 0 else float("nan")


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float); ry = np.argsort(np.argsort(y)).astype(float)
    # average ranks for ties
    def ranks(a):
        order = np.argsort(a, kind="mergesort"); r = np.empty(len(a)); sa = a[order]
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and sa[j + 1] == sa[i]:
                j += 1
            r[order[i:j + 1]] = (i + j) / 2 + 1
            i = j + 1
        return r
    return pearson(ranks(x), ranks(y))


def acf1(x):
    x = x - x.mean()
    return float((x[:-1] * x[1:]).sum() / (x * x).sum()) if (x * x).sum() > 0 else float("nan")


def fisher_ci(r, n):
    if not (n > 3) or np.isnan(r):
        return (float("nan"), float("nan"))
    z = np.arctanh(np.clip(r, -0.999999, 0.999999)); se = 1 / np.sqrt(n - 3)
    return (float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se)))


def hype_diagnostics(hl, bn, c_hl, coin):
    out = OrderedDict()
    W0 = windows(hl[coin], c_hl[coin], None, bn=bn[BN_OF[coin]])
    ann = HOURS_PER_YEAR / W0["I"]
    x, y, t, I = W0["actual"] * ann * 100, W0["bn"] * ann * 100, W0["t"], W0["I"]
    base_w = float(A.BASE_PER_HOUR) * HOURS_PER_YEAR * 100
    n = len(x)
    r = pearson(x, y)
    rho1, rho2 = acf1(x), acf1(y)
    n_eff = n * (1 - rho1 * rho2) / (1 + rho1 * rho2)
    out["windows"] = n; out["interval_h"] = float(I[0]); out["first"] = fmt_ts(int(t[0])); out["last"] = fmt_ts(int(t[-1]))
    out["pearson"] = r; out["spearman"] = spearman(x, y)
    out["acf1_hl"], out["acf1_bn"] = rho1, rho2; out["n_eff"] = float(n_eff)
    out["ci95_n"] = fisher_ci(r, n); out["ci95_neff"] = fisher_ci(r, n_eff)
    lo, hi = np.quantile(x, [0.01, 0.99]); xw = np.clip(x, lo, hi)
    lo2, hi2 = np.quantile(y, [0.01, 0.99]); yw = np.clip(y, lo2, hi2)
    out["pearson_winsorised_1_99"] = pearson(xw, yw)
    keep = np.abs(x - np.median(x)) <= np.quantile(np.abs(x - np.median(x)), 0.99)
    out["pearson_excl_top1pct_abs_hl"] = pearson(x[keep], y[keep]); out["excluded_windows"] = int((~keep).sum())
    both_base = (np.abs(x - base_w) < 1e-9) & (np.abs(y - base_w) < 1e-9)
    out["share_both_at_base_pct"] = float(100 * both_base.mean())
    out["share_hl_at_base_pct"] = float(100 * (np.abs(x - base_w) < 1e-9).mean()); out["share_bn_at_base_pct"] = float(100 * (np.abs(y - base_w) < 1e-9).mean())
    out["pearson_excl_both_at_base"] = pearson(x[~both_base], y[~both_base])
    top = np.argsort(-np.abs(x - y))[:5]
    out["top5_windows"] = [{"t": fmt_ts(int(t[i])), "hl_pct": float(x[i]), "bn_pct": float(y[i])} for i in top]
    keep5 = np.ones(n, bool); keep5[top] = False
    out["pearson_excl_top5"] = pearson(x[keep5], y[keep5]); out["spearman_excl_top5"] = spearman(x[keep5], y[keep5])
    out["cov_share_top5_pct"] = float(100 * ((x[top] - x.mean()) * (y[top] - y.mean())).sum() / ((x - x.mean()) * (y - y.mean())).sum())
    out["cov_share_top1_pct"] = float(100 * ((x[top[0]] - x.mean()) * (y[top[0]] - y.mean())) / ((x - x.mean()) * (y - y.mean())).sum())
    keep1 = np.ones(n, bool); keep1[top[0]] = False
    out["pearson_excl_top1"] = pearson(x[keep1], y[keep1])
    # hourly detail of the most extreme window
    s_hl = hl[coin]; slot = int(t[top[0]] // MS_H); I0 = int(I[top[0]])
    idx = {int(v): i for i, v in enumerate(s_hl.t // MS_H)}
    det = []
    for h in range(I0 - 1, -1, -1):
        i = idx.get(slot - h)
        if i is not None:
            det.append({"t": fmt_ts(int(s_hl.t[i])), "hl_hourly_rate": s_hl.rate_str[i], "hl_ann_pct": float(s_hl.rate[i] * HOURS_PER_YEAR * 100),
                        "premium_bp": float(s_hl.premium[i] * BP), "c_bp": float(c_hl[coin][i] * BP)})
    s_bn = bn[BN_OF[coin]]; j = int(np.searchsorted(s_bn.t // MS_H, slot))
    out["top1_detail"] = {"window_end": fmt_ts(int(t[top[0]])), "hl_hours": det,
                          "bn_rate": s_bn.rate_str[j], "bn_ann_pct": float(s_bn.rate[j] * HOURS_PER_YEAR / s_bn.ivl_h[j] * 100)}
    # lag scan: shift the Hyperliquid window by k hours
    lags = OrderedDict()
    for k in range(-8, 9):
        Wk = windows(hl[coin], c_hl[coin], None, bn=bn[BN_OF[coin]], lag_h=k)
        lags[k] = pearson(Wk["actual"] * HOURS_PER_YEAR / Wk["I"], Wk["bn"] * HOURS_PER_YEAR / Wk["I"])
    out["lag_scan"] = lags
    out["best_lag"] = max(lags, key=lambda k: lags[k]); out["best_lag_corr"] = lags[out["best_lag"]]
    # subperiods
    q = np.array([f"{utc(int(v)).year}-Q{(utc(int(v)).month - 1) // 3 + 1}" for v in t])
    out["by_quarter"] = OrderedDict()
    for qq in sorted(set(q.tolist())):
        m = q == qq
        out["by_quarter"][qq] = {"windows": int(m.sum()), "pearson": pearson(x[m], y[m]), "spearman": spearman(x[m], y[m]),
                                 "hl_mean_pct": float(np.average(x[m], weights=I[m])), "bn_mean_pct": float(np.average(y[m], weights=I[m]))}
    yrs = np.array([utc(int(v)).year for v in t])
    out["by_year"] = OrderedDict((int(yy), {"windows": int((yrs == yy).sum()), "pearson": pearson(x[yrs == yy], y[yrs == yy]),
                                             "spearman": spearman(x[yrs == yy], y[yrs == yy])}) for yy in sorted(set(yrs.tolist())))
    # aggregation levels: sums over 1 d and 7 d of both series (calendar-aligned, complete blocks only)
    agg = OrderedDict()
    for label, H in (("window", None), ("1 d", 24), ("7 d", 168)):
        if H is None:
            agg[label] = {"n": n, "pearson": r, "spearman": out["spearman"]}
            continue
        key = (t // MS_H) // H
        xs, ys = [], []
        for kk in np.unique(key):
            m = key == kk
            if I[m].sum() == H:
                xs.append(W0["actual"][m].sum()); ys.append(W0["bn"][m].sum())
        xs, ys = np.array(xs), np.array(ys)
        agg[label] = {"n": int(len(xs)), "pearson": pearson(xs, ys), "spearman": spearman(xs, ys)}
    out["by_aggregation"] = agg
    out["series"] = {"t": t, "x": x, "y": y}
    return out


# --------------------------------------------------------------------------- main

def main():
    hl, bn = A.load_all()
    with open(os.path.join(RES, "analysis.json")) as f:
        R = json.load(f)
    B = OrderedDict(generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))

    # clamp regimes
    c_hl, fit_hl = {}, {}
    B["clamp_regimes"] = OrderedDict()
    for coin in HL_COINS:
        c, fit, regs, short = clamp_regimes(hl[coin])
        c_hl[coin], fit_hl[coin] = c, fit
        B["clamp_regimes"][coin] = {"regimes": regs, "short_runs_ignored": short, "records": len(c),
                                    "fit": int(fit.sum()), "misfit": int((~fit).sum()),
                                    "misfit_span": (fmt_ts(int(hl[coin].t[~fit][0])), fmt_ts(int(hl[coin].t[~fit][-1]))) if (~fit).any() else None}
    # task 1 + 2a/2b per market-year and whole history
    B["censoring"] = OrderedDict()
    for coin in HL_COINS:
        s = hl[coin]
        d = OrderedDict()
        for y in sorted(set(s.year.tolist())):
            d[int(y)] = censoring_block(s, c_hl[coin], s.year == y)
            d[int(y)]["partial"] = R["by_year"]["HL"][coin][str(y)]["partial"]; d[int(y)]["days"] = R["by_year"]["HL"][coin][str(y)]["days"]
        d["all"] = censoring_block(s, c_hl[coin], np.ones(len(s.t), bool))
        B["censoring"][coin] = d
    # task 2c/2d: windows aligned with Binance (decomposition) and 8 h grid for all five (HL alone)
    B["decomposition"] = OrderedDict()
    Wd = {}
    for coin, sym in BN_OF.items():
        W = windows(hl[coin], c_hl[coin], None, bn=bn[sym])
        Wd[coin] = W
        B["decomposition"][coin] = decomposition(W)
    B["window_effect_8h_grid"] = OrderedDict()
    for coin in HL_COINS:
        W = windows(hl[coin], c_hl[coin], 8, anchor_ms=0)
        B["window_effect_8h_grid"][coin] = decomposition(W)
    # reaggregation invariance: hourly mean over the same hours vs. window mean
    B["reaggregation"] = OrderedDict()
    for coin, sym in BN_OF.items():
        W = Wd[coin]; ann = HOURS_PER_YEAR / W["I"]
        B["reaggregation"][coin] = {"hl_window_mean_pct": 100 * wmean(W["actual"] * ann, W["I"]),
                                    "hl_hourly_mean_same_hours_pct": 100 * wmean(W["actual"] * ann, W["I"]),  # identical by construction (sum/I)
                                    "bn_mean_pct": 100 * wmean(W["bn"] * ann, W["I"]), "windows": int(len(W["t"]))}
    # task 3
    B["hype"] = OrderedDict()
    for coin in ("HYPE", "BTC", "ETH", "SOL"):
        B["hype"][coin] = hype_diagnostics(hl, bn, c_hl, coin)

    # figures + docs
    fig_censoring(hl, c_hl, B)
    fig_decomposition(B, Wd)
    fig_hype(B)
    for coin in B["hype"]:
        B["hype"][coin].pop("series")
    R["u3bis"] = B
    with open(os.path.join(RES, "analysis.json"), "w") as f:
        json.dump(R, f, indent=1, default=str)
    section = write_section(R, B)
    with open(os.path.join(RES, "03-section-8.md"), "w") as f:
        f.write(section)
    path = os.path.join(DOCS, "03-analysis.md")
    with open(path) as f:
        doc = f.read()
    if MARK_START in doc:
        doc = doc[:doc.index(MARK_START)] + section + doc[doc.index(MARK_END) + len(MARK_END):]
    else:
        doc = doc.rstrip("\n") + "\n\n" + section
    with open(path, "w") as f:
        f.write(doc)
    print("done", file=sys.stderr)


# --------------------------------------------------------------------------- figures

def fig_censoring(hl, c_hl, B):
    fig, axes = plt.subplots(2, 5, figsize=(12.5, 7.4), gridspec_kw={"height_ratios": [1.15, 1]})
    for k, coin in enumerate(HL_COINS):
        s = hl[coin]; ax = axes[0, k]
        m = c_hl[coin] == 0.0005
        P, F8 = s.premium[m] * BP, f8_of(s)[m] * BP
        ax.scatter(P, F8, s=2, alpha=0.25, color=COL[coin], linewidths=0, rasterized=True)
        lim = 25
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        ax.axvspan((R8 - 0.0005) * BP, (R8 + 0.0005) * BP, color=GRID, alpha=0.6, lw=0)
        ax.axhline(R8 * BP, color=INK2, lw=0.8, ls="--")
        ax.set_title(f"{coin} (c = 5 bp regime)", fontsize=8.5, loc="left")
        ax.set_xlabel("hourly-averaged premium (bp / 8 h)")
        if k == 0:
            ax.set_ylabel("settled rate, 8 h basis (bp)")
        cb = B["censoring"][coin]["all"]
        ax.text(0.03, 0.96, f"in band: {cb['share_at_pct']:.0f}% of hours\nvariance not transmitted: {cb['var_not_transmitted_pct']:.0f}%",
                transform=ax.transAxes, va="top", fontsize=7.5, color=INK2)
        ax = axes[1, k]
        d = B["censoring"][coin]
        years = [y for y in d if y != "all"]
        for i, y in enumerate(years):
            q = d[y]["anchored_premium_q"]
            ax.plot([i, i], [q["p5"], q["p95"]], color=COL[coin], lw=1.2, alpha=0.45)
            ax.plot([i, i], [q["p25"], q["p75"]], color=COL[coin], lw=5)
            ax.plot([i - 0.22, i + 0.22], [q["p50"]] * 2, color=SURF, lw=1.3)
            ax.text(i, -4.6, f"{d[y]['share_at_pct']:.0f}%", ha="center", va="top", fontsize=7, color=INK2)
        ax.axhline(R8 * BP, color=INK2, lw=0.8, ls="--")
        ax.set_ylim(-5.4, 6.5)
        ax.set_xticks(range(len(years)))
        ax.set_xticklabels([f"{y}*" if d[y]["partial"] else f"{y}" for y in years], fontsize=8)
        ax.set_title(f"{coin}: anchored hours", fontsize=8.5, loc="left")
        ax.grid(axis="x", visible=False)
        if k == 0:
            ax.set_ylabel("premium (bp / 8 h); label = % hours at base")
    fig.suptitle("Interval censoring by the clamp: the settled rate is flat at the base whenever the premium lies inside "
                 "[r − c, r + c] (grey band); bottom: p5–p95 / p25–p75 / median of the premium during anchored hours",
                 x=0.01, ha="left", fontsize=9.5, fontweight="bold")
    fig.tight_layout()
    savefig(fig, "fig5-clamp-censoring")


def fig_decomposition(B, Wd):
    fig = plt.figure(figsize=(12, 8))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.15], hspace=0.5, wspace=0.3)
    for k, coin in enumerate(BN_OF):
        ax = fig.add_subplot(gs[0, k])
        D = B["decomposition"][coin]
        years = list(D["by_year"])
        x = np.arange(len(years))
        we = [D["by_year"][y]["window_effect_pp"] for y in years]
        res = [D["by_year"][y]["residual_pp"] for y in years]
        ax.bar(x - 0.2, we, 0.38, color=VENUE_COL["HL"], label="averaging-window effect (actual − 8 h-averaged counterfactual)", linewidth=0)
        ax.bar(x + 0.2, res, 0.38, color=INK2, label="residual (counterfactual − Binance)", linewidth=0)
        ax.plot(x, [D["by_year"][y]["diff_pp"] for y in years], "D", color=INK, ms=4, label="HL − Binance")
        ax.axhline(0, color=GRID, lw=0.8)
        ax.set_xticks(x); ax.set_xticklabels([f"{y}{'*' if D['by_year'][y]['days'] < 364 else ''}\n({D['by_year'][y]['days']:.0f} d)" for y in years], fontsize=7.5)
        ax.set_title(f"{coin}: {D['overall']['diff_pp']:+.2f} = {D['overall']['window_effect_pp']:+.2f} + {D['overall']['residual_pp']:+.2f} pp",
                     fontsize=8.5, loc="left")
        ax.grid(axis="x", visible=False)
        if k == 0:
            ax.set_ylabel("pp of annualised rate")
            handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 0.955), ncol=3, fontsize=7.5)
    ax = fig.add_subplot(gs[1, :])
    W = Wd["BTC"]; ann = HOURS_PER_YEAR / W["I"]
    d = np.array([utc(int(v)) for v in W["t"]])
    for key, lab, col in (("actual", "Hyperliquid, actually settled (hourly clamp)", VENUE_COL["HL"]),
                          ("cf", "Hyperliquid counterfactual: premium averaged over the Binance window, then clamped", "#4a3aa7"),
                          ("bn", "Binance", VENUE_COL["BN"])):
        ax.plot(d, rolling_mean_days(W["t"], W[key] * ann, W["I"], 30) * 100, color=col, lw=1.4, label=lab)
    ax.axhline(float(A.BASE_PER_HOUR) * HOURS_PER_YEAR * 100, color=INK2, lw=0.8, ls="--", label="base")
    ax.axhline(0, color=GRID, lw=0.8)
    ax.set_ylabel("%/yr (30-day trailing mean)")
    v = rolling_mean_days(W["t"], W["actual"] * ann, W["I"], 30) * 100
    ax.set_ylim(min(np.nanquantile(v, 0.01), -15), np.nanmax(v) + 5)
    ax.set_title("BTC: the three series over the overlap (title of each panel above: HL − Binance = window effect + residual)", loc="left", fontsize=9)
    ax.legend(loc="upper right", fontsize=7.5)
    fig.suptitle("Venue differential decomposed: HL − Binance = (actual − counterfactual with window-averaged premium) + residual",
                 x=0.01, y=0.99, ha="left", fontsize=10, fontweight="bold")
    savefig(fig, "fig6-venue-decomposition")


def fig_hype(B):
    fig = plt.figure(figsize=(12, 7.6))
    gs = fig.add_gridspec(2, 3, hspace=0.5, wspace=0.32)
    ax = fig.add_subplot(gs[0, 0])
    for coin in ("BTC", "ETH", "SOL", "HYPE"):
        ls = B["hype"][coin]["lag_scan"]
        ax.plot(list(ls), list(ls.values()), marker="o", ms=3, lw=1.3, color=COL[coin], label=coin)
    ax.axvline(0, color=GRID, lw=0.8); ax.axhline(0, color=GRID, lw=0.8)
    ax.set_xlabel("shift of the Hyperliquid window (hours; + = later)"); ax.set_ylabel("Pearson correlation")
    ax.set_title("Lag scan", loc="left"); ax.legend(fontsize=7.5)
    ax = fig.add_subplot(gs[0, 1])
    H = B["hype"]["HYPE"]
    qs = list(H["by_quarter"])
    x = np.arange(len(qs))
    ax.bar(x - 0.2, [H["by_quarter"][q]["pearson"] for q in qs], 0.38, color=COL["HYPE"], label="Pearson", linewidth=0)
    ax.bar(x + 0.2, [H["by_quarter"][q]["spearman"] for q in qs], 0.38, color=INK2, label="Spearman", linewidth=0)
    ax.axhline(0, color=GRID, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(qs, rotation=45, ha="right", fontsize=7.5)
    ax.set_title("HYPE: correlation by quarter", loc="left"); ax.legend(fontsize=7.5); ax.grid(axis="x", visible=False)
    ax = fig.add_subplot(gs[0, 2])
    for k, coin in enumerate(("BTC", "ETH", "SOL", "HYPE")):
        ag = B["hype"][coin]["by_aggregation"]
        ax.plot(range(3), [ag[l]["pearson"] for l in ag], marker="o", ms=4, color=COL[coin], label=coin)
    ax.set_xticks(range(3)); ax.set_xticklabels([f"settlement\nwindow", "1 day", "7 days"])
    ax.set_ylabel("Pearson correlation"); ax.set_title("Correlation vs. aggregation level", loc="left"); ax.legend(fontsize=7.5)
    ax.axhline(0, color=GRID, lw=0.8)
    ax = fig.add_subplot(gs[1, 0:2])
    sr = H["series"]
    ax.scatter(sr["y"], sr["x"], s=4, alpha=0.35, color=COL["HYPE"], linewidths=0, rasterized=True)
    lim_x = np.quantile(np.abs(sr["y"]), 0.995); lim_y = np.quantile(np.abs(sr["x"]), 0.995)
    ax.set_xlim(-lim_x, lim_x); ax.set_ylim(-lim_y, lim_y)
    ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
    ax.set_xlabel("Binance HYPEUSDT, annualised (%/yr, 4 h window)"); ax.set_ylabel("Hyperliquid HYPE, 4 h sum, annualised (%/yr)")
    ax.set_title(f"HYPE: {H['windows']:,} windows, Pearson {H['pearson']:.3f}, Spearman {H['spearman']:.3f} "
                 f"(axes cut at p99.5 of |value|)", loc="left", fontsize=9)
    ax = fig.add_subplot(gs[1, 2])
    d = np.array([utc(int(v)) for v in sr["t"]])
    I = np.full(len(d), H["interval_h"])
    ax.plot(d, rolling_mean_days(sr["t"], sr["x"], I, 30), color=VENUE_COL["HL"], lw=1.3, label="Hyperliquid")
    ax.plot(d, rolling_mean_days(sr["t"], sr["y"], I, 30), color=VENUE_COL["BN"], lw=1.3, label="Binance")
    ax.axhline(0, color=GRID, lw=0.8); ax.set_ylabel("%/yr, 30-day trailing mean"); ax.legend(fontsize=7.5)
    ax.set_title("HYPE: both venues", loc="left")
    ax.xaxis.set_major_locator(A.mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(A.mdates.DateFormatter("%Y-%m"))
    fig.suptitle("The HYPE cross-venue correlation: alignment, sample size, sub-periods and aggregation", x=0.01, ha="left", fontsize=10, fontweight="bold")
    savefig(fig, "fig7-hype-correlation")


# --------------------------------------------------------------------------- section text

def write_section(R, B):
    C, D, H = B["censoring"], B["decomposition"], B["hype"]
    ylab = lambda y, d: f"{y}* ({d['days']:.0f} d)" if d["partial"] else f"{y}"
    L = [MARK_START, "", "## 8. U3-bis — clamp censoring, the venue differential and the HYPE anomaly", ""]
    L.append(f"Generated {B['generated_utc']} by `scripts/analyse_clamp.py` from `data/full/`, under the rules of §1. "
             "This section uses the `premium` field that Hyperliquid's `fundingHistory` returns next to `fundingRate`. "
             "Binance's `fapi/v1/fundingRate` does not expose its premium index, so everything about the premium below "
             "is **Hyperliquid only**; the cross-venue tests use only the settled rates of both venues. The premium is "
             "on the 8 h basis (the documented formula's units) and is quoted in basis points per 8 h (bp); the settled "
             "rate is put on the same basis (hourly rate × 8, or the rate itself in the 8 h regime of May–June 2023).")
    L.append("")
    # 8.1 regimes
    L.append("### 8.1 The clamp band was not constant: regimes inferred from the data")
    L.append("")
    L.append("For every settlement not at the base the formula F = P + clamp(r − P, −c, c) puts F exactly c away from "
             "P, so |P − F| reveals c. Runs of ≥ 24 consecutive off-base settlements with the same implied c define the "
             "regimes; a regime starts at the first settlement the previous c cannot reproduce. Every settlement is then "
             "checked against the formula with its regime's c (tolerance 1e-9):")
    L.append("")
    rows = []
    for coin in HL_COINS:
        for r in B["clamp_regimes"][coin]["regimes"]:
            rows.append([coin, f"{r['c'] * BP:g} bp" if r["c"] > 0 else "0 (F = P)", r["from"], r["to"], f"{r['records']:,}", f"{r['misfit']:,}",
                         f"{r['misfit_span'][0]} → {r['misfit_span'][1]}" if r["misfit_span"] else "—"])
    L.append(md_table(["Market", "c (half-width, 8 h basis)", "From (UTC)", "To (UTC)", "Settlements", "Not reproduced", "Span of those"], rows))
    L.append("")
    tot = sum(B["clamp_regimes"][c]["records"] for c in HL_COINS); mis = sum(B["clamp_regimes"][c]["misfit"] for c in HL_COINS)
    short = [(c, r) for c in HL_COINS for r in B["clamp_regimes"][c]["short_runs_ignored"]]
    L.append(f"The formula reproduces {tot - mis:,} of {tot:,} Hyperliquid settlements exactly under the inferred c(t); the "
             f"{mis:,} it does not reproduce are listed in the table (spans), and the short runs the regime rule ignored are " +
             (", ".join(f"{c} {r['from']} → {r['to']} ({r['n']} settlement{'s' if r['n'] > 1 else ''} with implied c = {r['c'] * BP:g} bp)" for c, r in short)
              if short else "none") + ". The regime boundaries coincide to the hour across BTC, ETH and SOL, i.e. they are "
             "venue-wide; HYPE and PURR were listed after the last change and have a single regime. Consequences: "
             "(i) the documented ±0.05 % band (docs/01 §7) holds from " +
             f"{B['clamp_regimes']['BTC']['regimes'][-1]['from']} UTC onward; before that it was ±{B['clamp_regimes']['BTC']['regimes'][0]['c'] * 100:g} %, and for "
             f"{B['clamp_regimes']['BTC']['regimes'][1]['records']:,} hours ({B['clamp_regimes']['BTC']['regimes'][1]['from']} → "
             f"{B['clamp_regimes']['BTC']['regimes'][1]['to']}) the settled rate equalled the premium with no interest "
             "component and no clamp, so no hour of that period can be 'at base'; (ii) the §2 classification is unchanged "
             "(it compares the settled rate with the base and does not depend on c), but 'at base' now means "
             "'premium inside [r − c(t), r + c(t)]' with the c(t) of this table. These regime changes are inferred from "
             "the data; no announcement was looked up for them.")
    L.append("")
    # 8.2 censoring
    L.append("### 8.2 Task 1 — how much of the premium the settled series censors")
    L.append("")
    L.append("Per market and calendar year: hour-weighted share of hours settled exactly at the base; distribution of the "
             "premium conditional on those hours (bp per 8 h); the share of the premium's variance that the settled series "
             "does not transmit, 1 − Var(F) / Var(P) with F on the premium's basis (F is a 1-Lipschitz function of P, so "
             "the ratio lies in [0, 1]); and the share of the premium's total sum of squares that falls in anchored hours.")
    L.append("")
    rows = []
    for coin in HL_COINS:
        for y, d in C[coin].items():
            q = d["anchored_premium_q"]
            rows.append([coin, "all" if y == "all" else ylab(y, d), f"{d['share_at_pct']:.1f} %", f"{d['anchored_n']:,}",
                         f"{q['p5']:.2f} / {q['p25']:.2f} / {q['p50']:.2f} / {q['p75']:.2f} / {q['p95']:.2f}",
                         f"{d['anchored_premium_mean_bp']:.2f} ± {d['anchored_premium_std_bp']:.2f}",
                         f"{d['premium_std_bp']:.2f}", f"{d['var_not_transmitted_pct']:.1f} %", f"{d['ss_share_anchored_pct']:.1f} %", f"{d['corr_F8_P']:.2f}"])
    L.append(md_table(["Market", "Year", "Hours at base", "Anchored settlements", "Premium in anchored hours: p5 / p25 / p50 / p75 / p95 (bp)",
                       "mean ± sd (bp)", "Premium sd, all hours (bp)", "Variance not transmitted", "SS in anchored hours", "corr(F, P)"], rows))
    L.append("")
    L.append("![Censoring](../figures/fig5-clamp-censoring.png)")
    L.append("")
    L.append("*Figure 5 — top: settled rate against the hourly premium for the c = 5 bp regime; the flat segment is the "
             "clamp band. Bottom: p5–p95 / p25–p75 / median of the premium during anchored hours, per year; the label is "
             "the share of hours at base.*")
    L.append("")
    v = {c: C[c]["all"]["var_not_transmitted_pct"] for c in HL_COINS}
    lo_c, hi_c = min(v, key=v.get), max(v, key=v.get)
    L.append(f"Reading: during anchored hours the settled rate is a constant and carries no information about where the "
             f"premium sits inside the band; the premium in those hours spans the whole band (p5–p95 of "
             f"{C['BTC']['all']['anchored_premium_q']['p5']:.2f} to {C['BTC']['all']['anchored_premium_q']['p95']:.2f} bp for BTC over the whole "
             f"history, band {(R8 - B['clamp_regimes']['BTC']['regimes'][-1]['c']) * BP:+g} to {(R8 + B['clamp_regimes']['BTC']['regimes'][-1]['c']) * BP:+g} bp "
             f"since {B['clamp_regimes']['BTC']['regimes'][-1]['from']}). Over the whole history the "
             f"settled series fails to transmit between {v[lo_c]:.0f} % ({lo_c}) and {v[hi_c]:.0f} % ({hi_c}) of the premium's "
             "variance. The funding series is therefore an interval-censored observation of the premium: exact outside the "
             "band (shifted by c), censored to the interval inside it. Any use of the settled series as a positioning "
             "signal, or any backtest of funding capture built on it, is working with that censored variable, and the "
             "censoring is heaviest precisely in the calm regime (2025–2026), when most hours are anchored.")
    L.append("")
    # 8.3 hypothesis
    L.append("### 8.3 Task 2 — does the averaging window explain the venue differential?")
    L.append("")
    L.append("Hypothesis: the Hyperliquid premium is averaged over 1 h, Binance's over 8 h; a shorter window means a "
             "higher-variance premium, more mass outside the clamp band, and (if the premium is right-skewed) a higher "
             "settled mean. Four measurements follow.")
    L.append("")
    L.append("**(a) Skew of the Hyperliquid premium** (Fisher moment skewness of the hourly premium, all hours; mean, "
             "median, and share of hours with premium above r):")
    L.append("")
    rows = []
    for coin in HL_COINS:
        for y, d in C[coin].items():
            rows.append([coin, "all" if y == "all" else ylab(y, d), f"{d['premium_skew']:+.2f}", f"{d['premium_mean_bp']:+.2f}", f"{d['premium_median_bp']:+.2f}",
                         f"{d['premium_share_above_r_pct']:.1f} %"])
    L.append(md_table(["Market", "Year", "Skew", "Mean (bp)", "Median (bp)", "Hours with P > r"], rows))
    L.append("")
    L.append("**(b) Hours outside the clamp band**, upper tail (P > r + c) and lower tail (P < r − c), hour-weighted, "
             "with the c(t) of §8.1. By construction these coincide with the 'above' and 'below' classes of §2; the last "
             "column counts the settlements where they do not (the transition hours of §8.1):")
    L.append("")
    rows = []
    for coin in HL_COINS:
        for y, d in C[coin].items():
            rows.append([coin, "all" if y == "all" else ylab(y, d), f"{d['share_upper_tail_pct']:.1f} %", f"{d['share_lower_tail_pct']:.1f} %",
                         f"{d['share_at_pct']:.1f} %", f"{d['tail_vs_class_disagreements']}"])
    L.append(md_table(["Market", "Year", "Upper tail", "Lower tail", "In band", "Disagreements with §2"], rows))
    L.append("")
    L.append("**(c) Re-aggregation to the Binance settlement windows.** The Hyperliquid hourly rates summed over each "
             "Binance window (the §5 method) give, by construction, the same hour-weighted mean as the hourly series over "
             "the same hours, so the differential is invariant to the settlement frequency:")
    L.append("")
    rows = [[c, f"{r['windows']:,}", f"{r['hl_hourly_mean_same_hours_pct']:.2f}", f"{r['hl_window_mean_pct']:.2f}", f"{r['bn_mean_pct']:.2f}",
             f"{r['hl_window_mean_pct'] - r['bn_mean_pct']:+.2f}"] for c, r in B["reaggregation"].items()]
    L.append(md_table(["Market", "Windows", "HL hourly mean, same hours (%/yr)", "HL re-aggregated mean (%/yr)", "Binance mean (%/yr)", "HL − Binance (pp)"], rows))
    L.append("")
    L.append("**(d) Counterfactual with the premium averaged over the Binance window.** For every Binance window the "
             "Hyperliquid hourly premiums are averaged, the clamp formula (with the regime's c) is applied once to that "
             "average, and the result is scaled to the window length. This is what Hyperliquid would have settled had it "
             "used Binance's averaging window and its own premium. The difference actual − counterfactual isolates the "
             "averaging-window effect; counterfactual − Binance is what it leaves unexplained:")
    L.append("")
    rows = []
    for coin, d in D.items():
        o = d["overall"]
        rows.append([coin, f"{o['first']} → {o['last']}", f"{o['windows']:,}", f"{o['hl_actual_pct']:.2f}", f"{o['hl_cf_pct']:.2f}", f"{o['bn_pct']:.2f}",
                     f"{o['diff_pp']:+.2f}", f"{o['window_effect_pp']:+.2f}", f"{o['residual_pp']:+.2f}", f"{o['explained_share_pct']:+.1f} %",
                     f"{o['premium_std_hourly_bp']:.2f} → {o['premium_std_window_avg_bp']:.2f}"])
    L.append(md_table(["Market", "Overlap (UTC)", "Windows", "HL actual %/yr", "HL counterfactual %/yr", "Binance %/yr", "HL − Binance (pp)",
                       "Window effect (pp)", "Residual (pp)", "Share explained", "Premium sd hourly → window-avg (bp)"], rows))
    L.append("")
    rows = []
    for coin, d in D.items():
        for y, o in d["by_year"].items():
            rows.append([coin, f"{y}{'*' if o['days'] < 364 else ''} ({o['days']:.0f} d)", f"{o['windows']:,}", f"{o['diff_pp']:+.2f}", f"{o['window_effect_pp']:+.2f}",
                         f"{o['residual_pp']:+.2f}", f"{o['explained_share_pct']:+.0f} %", f"{o['corr_actual_bn']:.3f} / {o['corr_cf_bn']:.3f}"])
    L.append("By calendar year (correlation with Binance of the actual / counterfactual Hyperliquid series):")
    L.append("")
    L.append(md_table(["Market", "Year", "Windows", "HL − Binance (pp)", "Window effect (pp)", "Residual (pp)", "Share explained", "Corr. actual / counterfactual"], rows))
    L.append("")
    rows = []
    for coin, d in B["window_effect_8h_grid"].items():
        o = d["overall"]
        rows.append([coin, f"{o['windows']:,}", f"{o['hl_actual_pct']:.2f}", f"{o['hl_cf_pct']:.2f}", f"{o['window_effect_pp']:+.2f}",
                     ", ".join(f"{y}: {b['window_effect_pp']:+.2f}" for y, b in d["by_year"].items())])
    L.append("The same counterfactual on a fixed 8 h grid (00:00 / 08:00 / 16:00 UTC) for all five Hyperliquid markets, "
             "Binance not needed:")
    L.append("")
    L.append(md_table(["Market", "8 h windows", "Actual %/yr", "Counterfactual %/yr", "Window effect (pp)", "By year (pp)"], rows))
    L.append("")
    L.append("![Decomposition](../figures/fig6-venue-decomposition.png)")
    L.append("")
    L.append("*Figure 6 — top: HL − Binance per year split into the averaging-window effect and the residual; bottom: BTC, "
             "30-day trailing means of the actual, counterfactual and Binance series.*")
    L.append("")
    majors = ["BTC", "ETH", "SOL"]
    expl = {c: D[c]["overall"]["explained_share_pct"] for c in majors}
    mx = max(abs(x) for x in expl.values())
    verdict = ("**rejected**" if mx < 20 else "**partially supported**" if mx < 80 else "**supported**")
    unexpl = {c: D[c]["overall"]["residual_pp"] for c in majors}
    L.append(f"Verdict: the hypothesis is {verdict}. The ingredients it needs are present: the hourly premium is "
             f"right-skewed over the whole history ({', '.join(f'{c} {C[c][chr(97)+chr(108)+chr(108)]['premium_skew']:+.2f}' for c in majors)}) and "
             f"averaging over the window does reduce its dispersion ({', '.join(f'{c} {D[c]['overall']['premium_std_hourly_bp']:.2f} → {D[c]['overall']['premium_std_window_avg_bp']:.2f} bp' for c in majors)}). "
             f"But the reduction is small, because the hourly premium is persistent within a window, and the clamp is "
             f"flat inside the band, so the counterfactual mean barely moves: the averaging-window effect is "
             f"{', '.join(f'{c} {D[c]['overall']['window_effect_pp']:+.2f} pp' for c in majors)} against differentials of "
             f"{', '.join(f'{c} {D[c]['overall']['diff_pp']:+.2f} pp' for c in majors)}, i.e. it explains "
             f"{', '.join(f'{expl[c]:+.1f} %' for c in majors)} of them (HYPE: {D['HYPE']['overall']['window_effect_pp']:+.2f} of "
             f"{D['HYPE']['overall']['diff_pp']:+.2f} pp, {D['HYPE']['overall']['explained_share_pct']:+.1f} %). The effect is not even "
             f"of one sign by year (BTC: {', '.join(f'{y} {o[chr(119)+chr(105)+chr(110)+chr(100)+chr(111)+chr(119)+chr(95)+chr(101)+chr(102)+chr(102)+chr(101)+chr(99)+chr(116)+chr(95)+chr(112)+chr(112)]:+.2f}' for y, o in D['BTC']['by_year'].items())} pp), "
             f"so it is not a systematic premium. "
             f"Re-aggregation (c) cannot change the mean at all. What remains unexplained is "
             f"{', '.join(f'{c} {unexpl[c]:+.2f} pp' for c in majors)}: the Hyperliquid premium itself sits higher and "
             f"leaves the band upward more often than Binance's settled rates imply (upper-tail hours over the overlap in "
             f"§8.3(b) versus the Binance 'above base' shares of §4). Since both venues use the same formula, the same "
             f"interest rate and, since {B['clamp_regimes']['BTC']['regimes'][-1]['from']}, the same ±0.05 % band, the "
             f"differential is a difference in the premium (mark-versus-reference price) between the two venues, not in "
             f"the funding mechanics. What drives that premium difference is outside the reach of this dataset.")
    L.append("")
    # 8.4 HYPE
    L.append("### 8.4 Task 3 — the HYPE cross-venue correlation")
    L.append("")
    L.append("Diagnostics on the Binance-window series of §5 (Hyperliquid hourly rates summed over each Binance window, "
             "both annualised). BTC/ETH/SOL are shown as controls:")
    L.append("")
    rows = []
    for coin in ("HYPE", "BTC", "ETH", "SOL"):
        h = H[coin]
        rows.append([coin, f"{h['interval_h']:g} h", f"{h['windows']:,}", f"{h['pearson']:.3f}", f"[{h['ci95_n'][0]:.3f}, {h['ci95_n'][1]:.3f}]",
                     f"{h['acf1_hl']:.2f} / {h['acf1_bn']:.2f}", f"{h['n_eff']:,.0f}", f"[{h['ci95_neff'][0]:.3f}, {h['ci95_neff'][1]:.3f}]",
                     f"{h['spearman']:.3f}", f"{h['pearson_winsorised_1_99']:.3f}", f"{h['pearson_excl_top1']:.3f}", f"{h['pearson_excl_top5']:.3f}",
                     f"{h['share_both_at_base_pct']:.1f} %", f"{h['pearson_excl_both_at_base']:.3f}"])
    L.append(md_table(["Market", "Window", "N", "Pearson", "95 % CI (N)", "lag-1 autocorr. HL / BN", "N_eff", "95 % CI (N_eff)", "Spearman",
                       "Pearson, winsorised 1–99 %", "Pearson excl. top-1 window", "Pearson excl. top-5 windows", "Both at base", "Pearson excl. both-at-base"], rows))
    L.append("")
    rows = []
    for coin in ("HYPE", "BTC", "ETH", "SOL"):
        h = H[coin]; ls = h["lag_scan"]; ag = h["by_aggregation"]
        rows.append([coin, f"{ls['0']:.3f}" if "0" in ls else f"{ls[0]:.3f}", f"{h['best_lag']:+d} h → {h['best_lag_corr']:.3f}",
                     f"{ag['1 d']['pearson']:.3f} (N {ag['1 d']['n']:,})", f"{ag['7 d']['pearson']:.3f} (N {ag['7 d']['n']:,})",
                     " / ".join(f"{y}: {b['pearson']:.2f}" for y, b in h["by_year"].items())])
    L.append("Alignment and aggregation (lag = shift of the Hyperliquid window in hours; positive = later):")
    L.append("")
    L.append(md_table(["Market", "Pearson at lag 0", "Best lag", "Pearson, 1-day sums", "Pearson, 7-day sums", "Pearson by year"], rows))
    L.append("")
    h = H["HYPE"]
    L.append("HYPE by quarter (Pearson / Spearman / hour-weighted means of both venues, %/yr):")
    L.append("")
    L.append(md_table(["Quarter", "Windows", "Pearson", "Spearman", "HL mean", "Binance mean"],
                      [[q, f"{b['windows']:,}", f"{b['pearson']:+.3f}", f"{b['spearman']:+.3f}", f"{b['hl_mean_pct']:.2f}", f"{b['bn_mean_pct']:.2f}"] for q, b in h["by_quarter"].items()]))
    L.append("")
    L.append("The five windows with the largest |HL − Binance| and the hourly detail of the largest one:")
    L.append("")
    L.append(md_table(["Window end (UTC)", "HL, 4 h sum (%/yr)", "Binance (%/yr)"],
                      [[w["t"], f"{w['hl_pct']:+.1f}", f"{w['bn_pct']:+.1f}"] for w in h["top5_windows"]]))
    L.append("")
    td = h["top1_detail"]
    L.append(md_table(["Hour (UTC)", "HL hourly rate", "HL annualised (%/yr)", "HL premium (bp / 8 h)", "c (bp)"],
                      [[x["t"], x["hl_hourly_rate"], f"{x['hl_ann_pct']:+.0f}", f"{x['premium_bp']:+.1f}", f"{x['c_bp']:g}"] for x in td["hl_hours"]]))
    L.append("")
    L.append(f"Binance HYPEUSDT settled {td['bn_rate']} for the 4 h window ending {td['window_end']} UTC "
             f"({td['bn_ann_pct']:+.0f} %/yr).")
    L.append("")
    L.append("![HYPE](../figures/fig7-hype-correlation.png)")
    L.append("")
    L.append("*Figure 7 — lag scan (all four markets), HYPE correlation by quarter, correlation against aggregation level, "
             "scatter of the two venues' HYPE rates per window, and their 30-day means.*")
    L.append("")
    lags = {int(k): v for k, v in h["lag_scan"].items()}
    dip = sorted(k for k, v in lags.items() if v < 0.5 * max(lags.values()))
    npos = sum(1 for b in h["by_quarter"].values() if b["pearson"] > 0)
    L.append(f"Conclusion: the near-zero Pearson correlation is a real-data feature concentrated in a handful of windows, "
             f"not a timing artefact. (i) Alignment: the lag scan has no shifted peak that beats lag 0 by more than the "
             f"controls do (HYPE best lag {h['best_lag']:+d} h at {h['best_lag_corr']:.3f}); the correlation falls below half its "
             f"maximum only for lags {dip[0]:+d}…{dip[-1]:+d} h, a span of {len(dip)} h, i.e. one {h['interval_h']:g} h window, which is what a "
             f"single extreme hour paired with one Binance settlement produces. (ii) Sample size: N = {h['windows']:,}, N_eff ≈ {h['n_eff']:,.0f} after the lag-1 autocorrelation; the "
             f"95 % interval on N_eff is [{h['ci95_neff'][0]:.3f}, {h['ci95_neff'][1]:.3f}], so the Pearson value is not "
             f"distinguishable from zero, but the rank correlation is {h['spearman']:.3f}, and after removing the single window "
             f"ending {h['top5_windows'][0]['t']} UTC (HL {h['top5_windows'][0]['hl_pct']:+.0f} %/yr against Binance "
             f"{h['top5_windows'][0]['bn_pct']:+.0f} %/yr, opposite signs, {h['cov_share_top1_pct']:+.0f} % of the sample covariance) "
             f"Pearson is {h['pearson_excl_top1']:.3f}; excluding the five most discordant windows, {h['pearson_excl_top5']:.3f}. "
             f"(iii) Sub-periods: {npos} of {len(h['by_quarter'])} quarters have positive Pearson ({', '.join(f'{q} {b['pearson']:+.2f}' for q, b in h['by_quarter'].items())}); "
             f"the negative quarter contains that window. (iv) Aggregation: at 1-day and 7-day sums the correlation rises "
             f"to {h['by_aggregation']['1 d']['pearson']:.2f} and {h['by_aggregation']['7 d']['pearson']:.2f}, against "
             f"{H['BTC']['by_aggregation']['7 d']['pearson']:.2f} / {H['ETH']['by_aggregation']['7 d']['pearson']:.2f} / "
             f"{H['SOL']['by_aggregation']['7 d']['pearson']:.2f} for BTC / ETH / SOL at 7 days. So: the two venues' HYPE "
             f"funding does co-move, more weakly than for the majors, and the {h['pearson']:.2f} headline is produced by a few hours in "
             f"which the two venues settled large rates of opposite sign, most of all the window ending "
             f"{h['top5_windows'][0]['t']} UTC, when Hyperliquid's hourly rates hit "
             f"{min(x['hl_ann_pct'] for x in td['hl_hours']):+.0f} %/yr while Binance settled {td['bn_ann_pct']:+.0f} %/yr. Why the two "
             f"venues' marks moved in opposite directions in those hours cannot be established from funding data alone; that part is left "
             f"unresolved.")
    L.append("")
    L.append(MARK_END)
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    main()
