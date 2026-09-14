#!/usr/bin/env python3
"""Reproducible download of the nine funding-rate series used in this study.

    python3 scripts/download.py            # all nine series into data/downloaded/
    python3 scripts/download.py --only hl  # or --only binance
    python3 scripts/download.py --end 2026-09-10T16:00:00Z

Public endpoints only, no credentials, no third-party packages (stdlib only,
Python >= 3.9). Output format is one JSON object per line, serialised with
json.dumps default separators and the field order returned by the API — the
same layout as data/baseline/.

The settlement interval is never assumed: it is derived per series from the
delta between consecutive timestamps and written to data/downloaded/intervals.json
(and printed as a table). See docs/02-download.md.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

HL_URL = "https://api.hyperliquid.xyz/info"
BN_URL = "https://fapi.binance.com/fapi/v1/fundingRate"

HL_COINS = ["BTC", "ETH", "SOL", "HYPE", "PURR"]
BN_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT"]

# Baseline window start for Hyperliquid (first record of data/baseline/funding-*.jsonl).
HL_DEFAULT_START_MS = 1757476800000  # 2025-09-10 04:00:00 UTC
# Binance: startTime=0 is treated as "absent" by the API and returns the latest
# records, so "from the beginning" is startTime=1.
BN_DEFAULT_START_MS = 1

HL_PAGE_CAP = 500      # observed hard cap per fundingHistory call (docs do not state it)
BN_PAGE_LIMIT = 1000   # documented max for /fapi/v1/fundingRate

# Rate-limit pacing. Hyperliquid: 1200 weight/min/IP; fundingHistory costs 20 + 1 per
# 20 items returned (500 items -> 45). Binance: /fapi/v1/fundingRate shares a
# 500-requests-per-5-minutes limiter with /fapi/v1/fundingInfo.
HL_WEIGHT_BUDGET_PER_MIN = 1000   # keep headroom under 1200
BN_MIN_SECONDS_BETWEEN_CALLS = 0.7  # ~86/min < 100/min

MAX_ATTEMPTS = 6
TIMEOUT_S = 30
UA = "perp-funding-study/U2 (+github: molinamanlio)"


class GeoBlocked(RuntimeError):
    pass


def log(msg):
    print(f"[{dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def utc(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)


def parse_iso_ms(s):
    if s is None:
        return None
    s = s.replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return int(d.timestamp() * 1000)


# --------------------------------------------------------------------------- HTTP

def request_json(url, *, method="GET", body=None, params=None):
    """One HTTP call with the retry policy documented in docs/02-download.md.

    - 451 (Binance geographic block): abort immediately, no retry.
    - 418 (Binance IP ban) / 429: wait Retry-After if present, else exponential backoff.
    - 5xx, timeouts, connection errors: exponential backoff 1,2,4,8,16 s, 6 attempts.
    - 4xx other than the above: abort (a bug in the request, retrying will not help).
    """
    if params:
        from urllib.parse import urlencode
        url = url + "?" + urlencode(params)
    data = None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    delay = 1.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode()), dict(resp.headers)
        except urllib.error.HTTPError as e:
            text = e.read().decode(errors="replace")[:300]
            if e.code == 451:
                raise GeoBlocked(
                    f"HTTP 451 from {url}: {text!r}. Binance blocks this IP's region; "
                    "see docs/02-download.md §Geographic restriction.")
            if e.code in (418, 429):
                ra = e.headers.get("Retry-After")
                wait = float(ra) if ra else delay
                log(f"HTTP {e.code} (rate limit/ban) attempt {attempt}: waiting {wait:.0f}s. body={text!r}")
                time.sleep(wait)
            elif 500 <= e.code < 600:
                log(f"HTTP {e.code} attempt {attempt}: waiting {delay:.0f}s. body={text!r}")
                time.sleep(delay)
            else:
                raise RuntimeError(f"HTTP {e.code} from {url}: {text!r}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            log(f"network error attempt {attempt}: {e!r}; waiting {delay:.0f}s")
            time.sleep(delay)
        delay = min(delay * 2, 16)
    raise RuntimeError(f"giving up on {url} after {MAX_ATTEMPTS} attempts")


class HLPacer:
    """Sliding-window weight budget for Hyperliquid (1200/min/IP)."""

    def __init__(self, budget=HL_WEIGHT_BUDGET_PER_MIN):
        self.budget = budget
        self.spent = []  # (t, weight)

    def wait_for(self, weight):
        while True:
            now = time.monotonic()
            self.spent = [(t, w) for t, w in self.spent if now - t < 60]
            if sum(w for _, w in self.spent) + weight <= self.budget:
                return
            time.sleep(0.5)

    def record(self, weight):
        self.spent.append((time.monotonic(), weight))


# --------------------------------------------------------------------------- fetchers

def fetch_hyperliquid(coin, start_ms, end_ms, pacer):
    """fundingHistory, ascending, paged on startTime = last.time + 1.

    startTime and endTime are inclusive (verified 2026-09-14). At most 500 rows per
    call. Stop when a page comes back with fewer than 500 rows or is empty.
    """
    rows = []
    cursor = start_ms
    calls = 0
    while True:
        weight = 20 + HL_PAGE_CAP // 20
        pacer.wait_for(weight)
        body = {"type": "fundingHistory", "coin": coin, "startTime": cursor}
        if end_ms is not None:
            body["endTime"] = end_ms
        page, _ = request_json(HL_URL, method="POST", body=body)
        pacer.record(20 + max(1, len(page)) // 20)
        calls += 1
        if not page:
            break
        for r in page:
            if rows and r["time"] <= rows[-1]["time"]:
                raise RuntimeError(f"{coin}: non-monotonic page at {r['time']}")
        rows.extend(page)
        if len(page) < HL_PAGE_CAP:
            break
        cursor = page[-1]["time"] + 1
    log(f"HL {coin}: {len(rows)} records in {calls} calls")
    return rows


def fetch_binance(symbol, start_ms, end_ms):
    """/fapi/v1/fundingRate, ascending, paged on startTime = last.fundingTime + 1.

    startTime and endTime are inclusive (verified 2026-09-14). limit max 1000. Stop on
    a short page or an empty one.
    """
    rows = []
    cursor = start_ms
    calls = 0
    last_call = 0.0
    while True:
        wait = BN_MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - last_call)
        if wait > 0:
            time.sleep(wait)
        params = {"symbol": symbol, "startTime": cursor, "limit": BN_PAGE_LIMIT}
        if end_ms is not None:
            params["endTime"] = end_ms
        last_call = time.monotonic()
        page, _ = request_json(BN_URL, params=params)
        calls += 1
        if not page:
            break
        for r in page:
            if rows and r["fundingTime"] <= rows[-1]["fundingTime"]:
                raise RuntimeError(f"{symbol}: non-monotonic page at {r['fundingTime']}")
        rows.extend(page)
        if len(page) < BN_PAGE_LIMIT:
            break
        cursor = page[-1]["fundingTime"] + 1
    log(f"Binance {symbol}: {len(rows)} records in {calls} calls")
    return rows


# --------------------------------------------------------------------------- intervals

def interval_report(times_ms):
    """Group consecutive deltas into runs of equal interval (rounded to the minute).

    Nothing is assumed: the rounding only absorbs the sub-second settlement jitter, and
    the raw min/max delta of every run is kept so the jitter itself is visible.
    """
    runs = []
    for i in range(1, len(times_ms)):
        d = times_ms[i] - times_ms[i - 1]
        minutes = round(d / 60000)
        if runs and runs[-1]["interval_minutes"] == minutes:
            r = runs[-1]
            r["to"] = times_ms[i]
            r["deltas"] += 1
            r["delta_ms_min"] = min(r["delta_ms_min"], d)
            r["delta_ms_max"] = max(r["delta_ms_max"], d)
        else:
            runs.append({"interval_minutes": minutes, "from": times_ms[i - 1], "to": times_ms[i],
                         "deltas": 1, "delta_ms_min": d, "delta_ms_max": d})
    for r in runs:
        r["interval_hours"] = r["interval_minutes"] / 60
        r["from_utc"] = utc(r["from"]).strftime("%Y-%m-%d %H:%M")
        r["to_utc"] = utc(r["to"]).strftime("%Y-%m-%d %H:%M")
    return runs


def print_interval_table(report):
    print("\nDetected settlement intervals (derived from consecutive timestamps):\n")
    print("| Series | Interval | From (UTC) | To (UTC) | Deltas | Raw delta min..max (ms) |")
    print("|---|---|---|---|---|---|")
    for name, runs in report.items():
        for r in runs:
            print(f"| {name} | {r['interval_hours']:g} h | {r['from_utc']} | {r['to_utc']} | "
                  f"{r['deltas']:,} | {r['delta_ms_min']:,}..{r['delta_ms_max']:,} |")


# --------------------------------------------------------------------------- main

def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/downloaded")
    ap.add_argument("--only", choices=["hl", "binance"], help="download one venue only")
    ap.add_argument("--hl-start", default=None,
                    help=f"ISO-8601 UTC; default {utc(HL_DEFAULT_START_MS).isoformat()} (baseline window start)")
    ap.add_argument("--binance-start", default=None, help="ISO-8601 UTC; default: from the first record (startTime=1)")
    ap.add_argument("--end", default=None, help="ISO-8601 UTC, inclusive, both venues; default: now")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    end_ms = parse_iso_ms(args.end)
    hl_start = parse_iso_ms(args.hl_start) if args.hl_start else HL_DEFAULT_START_MS
    bn_start = parse_iso_ms(args.binance_start) if args.binance_start else BN_DEFAULT_START_MS
    started = dt.datetime.now(dt.timezone.utc)
    report = {}
    manifest = {"started_utc": started.isoformat(), "end_param_ms": end_ms,
                "hl_start_ms": hl_start, "binance_start_ms": bn_start, "series": {}}

    try:
        if args.only != "binance":
            pacer = HLPacer()
            for coin in HL_COINS:
                rows = fetch_hyperliquid(coin, hl_start, end_ms, pacer)
                name = f"funding-{coin}.jsonl"
                write_jsonl(os.path.join(args.out, name), rows)
                report[name] = interval_report([r["time"] for r in rows])
                manifest["series"][name] = {"records": len(rows),
                                            "first": rows[0]["time"] if rows else None,
                                            "last": rows[-1]["time"] if rows else None}
        if args.only != "hl":
            for sym in BN_SYMBOLS:
                rows = fetch_binance(sym, bn_start, end_ms)
                name = f"binance-funding-{sym}.jsonl"
                write_jsonl(os.path.join(args.out, name), rows)
                report[name] = interval_report([r["fundingTime"] for r in rows])
                manifest["series"][name] = {"records": len(rows),
                                            "first": rows[0]["fundingTime"] if rows else None,
                                            "last": rows[-1]["fundingTime"] if rows else None}
    except GeoBlocked as e:
        log(str(e))
        sys.exit(3)

    manifest["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    with open(os.path.join(args.out, "intervals.json"), "w") as f:
        json.dump(report, f, indent=1)
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print_interval_table(report)
    log(f"done; output in {args.out}/")


if __name__ == "__main__":
    main()
