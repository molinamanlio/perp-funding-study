#!/usr/bin/env python3
"""Record-by-record comparison of data/downloaded/ against data/baseline/.

    python3 scripts/verify.py [--baseline data/baseline] [--downloaded data/downloaded]

For every series the key is the exact settlement timestamp in ms (`time` for
Hyperliquid, `fundingTime` for Binance). Reported per series:

  identical           same timestamp, every field byte-equal
  differ              same timestamp, at least one field differs (listed by field)
  only in baseline    timestamp present in baseline, absent in downloaded
  only in downloaded  timestamp present in downloaded, absent in baseline

Nothing is corrected, normalised or dropped. As a diagnostic only, the "only in"
records are additionally split into those inside/outside the baseline's time span,
and pairs that share the same minute (i.e. differ only in ms jitter) are counted.
Also checks whether each downloaded file is byte-identical to the baseline
(SHA-256), which is not required but is informative.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from collections import Counter

SERIES = [("funding-BTC.jsonl", "time"), ("funding-ETH.jsonl", "time"), ("funding-SOL.jsonl", "time"),
          ("funding-HYPE.jsonl", "time"), ("funding-PURR.jsonl", "time"),
          ("binance-funding-BTCUSDT.jsonl", "fundingTime"), ("binance-funding-ETHUSDT.jsonl", "fundingTime"),
          ("binance-funding-SOLUSDT.jsonl", "fundingTime"), ("binance-funding-HYPEUSDT.jsonl", "fundingTime")]


def utc(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def load(path, key):
    rows = {}
    with open(path) as f:
        for n, line in enumerate(f, 1):
            r = json.loads(line)
            if r[key] in rows:
                raise SystemExit(f"{path}:{n}: duplicate key {r[key]}")
            rows[r[key]] = (r, line.rstrip("\n"))
    return rows


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compare(name, key, bpath, dpath):
    b, d = load(bpath, key), load(dpath, key)
    bk, dk = set(b), set(d)
    common = bk & dk
    identical, differ, diff_fields = 0, [], Counter()
    for k in common:
        rb, lb = b[k]
        rd, ld = d[k]
        if lb == ld:
            identical += 1
        else:
            fields = [f for f in set(rb) | set(rd) if rb.get(f) != rd.get(f)]
            if not fields:
                fields = ["<serialisation only>"]
            differ.append((k, fields, rb, rd))
            diff_fields.update(fields)
    only_b = sorted(bk - dk)
    only_d = sorted(dk - bk)
    b_first, b_last = min(bk), max(bk)
    only_d_inside = [k for k in only_d if b_first <= k <= b_last]
    only_d_after = [k for k in only_d if k > b_last]
    only_d_before = [k for k in only_d if k < b_first]
    # jitter diagnostic: same minute on both sides but different ms
    minute_b = {k // 60000 for k in only_b}
    minute_d = {k // 60000 for k in only_d}
    jitter_pairs = len(minute_b & minute_d)
    return {
        "series": name, "baseline_records": len(b), "downloaded_records": len(d),
        "identical": identical, "differ": len(differ), "differ_fields": dict(diff_fields),
        "differ_examples": [(k, utc(k), f, rb, rd) for k, f, rb, rd in sorted(differ)[:5]],
        "only_baseline": len(only_b), "only_baseline_examples": [utc(k) for k in only_b[:5]],
        "only_downloaded": len(only_d),
        "only_downloaded_before_span": len(only_d_before), "only_downloaded_inside_span": len(only_d_inside),
        "only_downloaded_after_span": len(only_d_after),
        "only_downloaded_inside_examples": [utc(k) for k in only_d_inside[:5]],
        "same_minute_pairs_among_only": jitter_pairs,
        "baseline_span": (utc(b_first), utc(b_last)),
        "downloaded_span": (utc(min(dk)), utc(max(dk))),
        "sha_equal": sha256(bpath) == sha256(dpath),
        "downloaded_sha256": sha256(dpath),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="data/baseline")
    ap.add_argument("--downloaded", default="data/downloaded")
    ap.add_argument("--json", default=None, help="also write the full result here")
    args = ap.parse_args()
    results = []
    for name, key in SERIES:
        bp, dp = os.path.join(args.baseline, name), os.path.join(args.downloaded, name)
        if not os.path.exists(dp):
            print(f"MISSING downloaded file: {dp}")
            continue
        results.append(compare(name, key, bp, dp))

    print("| Series | Baseline | Downloaded | Identical | Differ in value | Only in baseline | Only in downloaded (before / inside / after baseline span) | Byte-identical file |")
    print("|---|---|---|---|---|---|---|---|")
    for r in results:
        print(f"| {r['series']} | {r['baseline_records']:,} | {r['downloaded_records']:,} | {r['identical']:,} | "
              f"{r['differ']:,} | {r['only_baseline']:,} | {r['only_downloaded']:,} "
              f"({r['only_downloaded_before_span']} / {r['only_downloaded_inside_span']} / {r['only_downloaded_after_span']}) | "
              f"{'yes' if r['sha_equal'] else 'no'} |")
    print()
    for r in results:
        if r["differ"] or r["only_baseline"] or r["only_downloaded_inside_span"] or r["only_downloaded_before_span"]:
            print(f"### {r['series']}")
            if r["differ"]:
                print(f"- differ by field: {r['differ_fields']}")
                for k, t, f, rb, rd in r["differ_examples"]:
                    print(f"  - {t} ({k}) fields {f}\n    baseline:   {json.dumps(rb)}\n    downloaded: {json.dumps(rd)}")
            if r["only_baseline"]:
                print(f"- only in baseline (first 5): {r['only_baseline_examples']}")
            if r["only_downloaded_inside_span"] or r["only_downloaded_before_span"]:
                print(f"- only in downloaded inside/before baseline span (first 5): {r['only_downloaded_inside_examples']}")
            if r["same_minute_pairs_among_only"]:
                print(f"- pairs of 'only in' records that share the same minute (ms jitter differs): {r['same_minute_pairs_among_only']}")
            print()
    print("Spans (first .. last timestamp, UTC):")
    for r in results:
        print(f"- {r['series']}: baseline {r['baseline_span'][0]} .. {r['baseline_span'][1]}; "
              f"downloaded {r['downloaded_span'][0]} .. {r['downloaded_span'][1]}")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=1, default=str)


if __name__ == "__main__":
    main()
