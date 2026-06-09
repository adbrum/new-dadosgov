"""Load test: prove the WAF IP-collapse blocks PUBLIC SEARCH behind the F5.

Context (docs/infra-adc-waf-impact-ppr-prd.md, incident 4.2): behind the F5 the
backend sees every visitor with the same origin IP. The three public search
endpoints that populate the listing pages —

    GET /api/1/datasets/?q=...        (pages/datasets   search)
    GET /api/1/organizations/?q=...   (pages/organizations search)
    GET /api/1/reuses/?q=...          (pages/reuses     search)

— have NO per-endpoint limit (udata/api/limits.py only covers content-creation
and the per-user identity poll). They are ANONYMOUS, so they cannot be keyed
per user the way GET /me was fixed: every anonymous request falls under the
IP-keyed global ceiling RATELIMIT_DEFAULT = "1000 per day; 200 per hour"
(udata.cfg, Redis-backed -> shared across all workers).

Behind the F5/WAF (emulated on TST nginx via `proxy_set_header X-Forwarded-For
10.0.0.1`) EVERY visitor's search collapses into that single 10.0.0.1 bucket.
So the *aggregate* of all visitors' searches — not each visitor — exhausts the
200/hour ceiling, after which every further search returns 429 and the listing
pages render empty ("o WAF bloqueia o pedido para popular as paginas").

This script reproduces the symptom: it fires anonymous search requests, each
carrying a DISTINCT spoofed X-Forwarded-For (i.e. pretending to be a different
visitor). The WAF nginx overwrites them all to 10.0.0.1, so they collapse and
start 429ing once the shared hourly bucket is spent.

  Phase 0 (traversal)  One warm-up request per endpoint; asserts 200 and checks
                       for the ADC-injected `cookiesession1` cookie -> evidence
                       the WAF-emulating nginx was actually traversed.
  Phase 1 (collapse)   N anonymous searches, round-robin across the 3 endpoints
                       with rotating queries and distinct spoofed XFF per
                       request. Records the ordered status stream and reports
                       the request index where the first block (429) appears.

EXPECTED behind the WAF:  the first ~200 searches answer 200, then 429 for the
rest of the hour -> CONFIRMS public search is collapsible and DoS-able by
aggregate volume. EXPECTED with no collapse / limiter off: zero 429.

WARNING — SIDE EFFECT: tripping the 200/hour IP bucket blocks ALL anonymous
traffic from the collapsed IP (i.e. every real TST visitor) for the remainder
of the clock hour. Run only on TST/PPR, never casually on PRD.

Usage (from repo root):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url https://10.55.37.38 --insecure

    # stop as soon as blocking is demonstrated (don't waste the whole bucket):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url https://10.55.37.38 --insecure --stop-on-block

    # dry-run against a local stack (no WAF, single host -> still collapses):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url http://localhost:3000
"""

from __future__ import annotations

import argparse
import itertools
import statistics
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    import urllib3
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("requests not installed - run via: uv run --with requests python scripts/...")

# Public search endpoints that populate the three listing pages. Path + the
# label shown in the report. All are GET, anonymous, and fall under the IP-keyed
# RATELIMIT_DEFAULT because limits.py defines no per-endpoint override for them.
SEARCH_ENDPOINTS = [
    ("datasets", "/api/1/datasets/"),
    ("organizations", "/api/1/organizations/"),
    ("reuses", "/api/1/reuses/"),
]

# Aggregated listing endpoints (LEDG-1836) that power the SSR /pages/* listing
# pages. Next.js fetches these server-side on every page load / pagination /
# filter, so all visitors reach the backend as ONE origin IP (the frontend
# server) and collapse independently of the F5. Same PUBLIC_SEARCH_LIMIT applies
# after the fix. Target them with --only site-datasets|site-organizations|
# site-reuses.
SITE_LISTING_ENDPOINTS = [
    ("site-datasets", "/api/1/site/datasets-listing/"),
    ("site-organizations", "/api/1/site/organizations-listing/"),
    ("site-reuses", "/api/1/site/reuses-listing/"),
]

ALL_ENDPOINTS = SEARCH_ENDPOINTS + SITE_LISTING_ENDPOINTS

# Rotating query terms so requests look like real distinct searches rather than
# one cached query. Content is irrelevant to the rate limiter (it keys on IP),
# but varied queries also defeat any per-query response caching on the way.
QUERIES = [
    "ambiente", "saude", "educacao", "transportes", "economia", "energia",
    "turismo", "cultura", "agricultura", "justica", "habitacao", "clima",
    "covid", "orcamento", "mobilidade", "censos", "florestas", "agua",
    "emprego", "demografia",
]

# Mirrored from udata.cfg: the IP-keyed global ceiling these endpoints inherit.
SHARED_BUCKET_PER_HOUR = 200  # RATELIMIT_DEFAULT "200 per hour"
SHARED_BUCKET_PER_DAY = 1000  # RATELIMIT_DEFAULT "1000 per day"

F5_COOKIE = "cookiesession1"  # injected by the ADC / emulated by TST nginx

print_lock = threading.Lock()


def log(msg: str) -> None:
    with print_lock:
        print(msg, flush=True)


def spoofed_ip(n: int) -> str:
    """A distinct, syntactically valid public-ish IP per request, so each call
    pretends to be a different visitor. The WAF nginx overwrites this with
    10.0.0.1; sending it documents intent and makes a no-WAF run a useful
    control (distinct IPs would each get their own bucket without the collapse).
    """
    return f"203.0.{(n // 254) % 254}.{(n % 254) + 1}"  # 203.0.0.0/16 (TEST-NET-ish)


def search_once(
    session: requests.Session,
    base_url: str,
    n: int,
    xff: str,
    endpoints: list[tuple[str, str]],
    verify: bool,
) -> tuple[int, str, int, float]:
    """One anonymous search. Returns (n, endpoint_label, status, latency_s).
    status 0 = transport error.

    `xff` is the X-Forwarded-For sent. A DISTINCT value per request (control)
    keys each call to its own bucket -> no block. A CONSTANT value (collapse
    mode) emulates the F5/WAF presenting one origin IP -> shared bucket -> 429.
    Page is pinned to 1 so tiny result sets (organizations total=6, reuses
    total=1) don't return out-of-range 404s that would pollute the signal; the
    limiter counts every request regardless of page or status."""
    label, path = endpoints[n % len(endpoints)]
    query = QUERIES[n % len(QUERIES)]
    url = f"{base_url}{path}?q={query}&page=1&page_size=20"
    start = time.monotonic()
    try:
        resp = session.get(
            url,
            headers={"Accept": "application/json", "X-Forwarded-For": xff},
            timeout=30,
        )
        return n, label, resp.status_code, time.monotonic() - start
    except requests.RequestException:
        return n, label, 0, time.monotonic() - start


def warm_up(base_url: str, verify: bool) -> bool:
    """Phase 0: one request per endpoint; assert reachable + report WAF cookie.
    Returns True if traffic appears to traverse the emulated WAF."""
    print("\n=== Phase 0: reachability + WAF traversal ===")
    session = requests.Session()
    session.verify = verify
    traversed = False
    for label, path in SEARCH_ENDPOINTS:
        url = f"{base_url}{path}?q=ambiente&page=1&page_size=1"
        try:
            resp = session.get(url, headers={"Accept": "application/json"}, timeout=30)
        except requests.RequestException as exc:
            print(f"  [!] {label}: request failed ({exc})")
            return False
        total = None
        try:
            total = resp.json().get("total")
        except ValueError:
            pass
        print(f"  [{resp.status_code}] {label}: total={total}")
        if resp.status_code != 200:
            print(f"  [!] {label} did not return 200 on a single request - aborting")
            return False
    if F5_COOKIE in session.cookies:
        print(f"  WAF traversal confirmed: {F5_COOKIE} cookie present")
        traversed = True
    else:
        print(
            f"  [!] no {F5_COOKIE} cookie - WAF emulation may NOT be live "
            "(apply nginx.conf + `sudo systemctl reload nginx`). Continuing; a "
            "single-host run still collapses to one IP, but cross-visitor proof "
            "depends on the WAF overwriting X-Forwarded-For."
        )
    return traversed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base-url",
        default="https://10.55.37.38",
        help="Frontend origin to test through (default: TST behind emulated WAF).",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=260,
        help="Total anonymous searches to fire (default 260 -> just past the "
        f"{SHARED_BUCKET_PER_HOUR}/hour ceiling to show the block kicking in).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Concurrent workers (default 10). Order of completion is recorded "
        "by request index, not arrival, so the block threshold stays readable.",
    )
    parser.add_argument(
        "--stop-on-block",
        action="store_true",
        help="Stop firing as soon as the first 429/403 is seen (preserves the "
        "rest of the hourly bucket for normal TST use).",
    )
    parser.add_argument(
        "--only",
        choices=[label for label, _ in ALL_ENDPOINTS],
        default=None,
        help="Hammer a SINGLE endpoint instead of round-robin. Required to trip "
        "the limit: flask-limiter's default_limits are PER-ENDPOINT, so spreading "
        f"requests across the 3 endpoints needs 3x{SHARED_BUCKET_PER_HOUR} to "
        "block. With --only, 200+ requests to one endpoint trip its bucket.",
    )
    parser.add_argument(
        "--collapse-ip",
        default=None,
        metavar="IP",
        help="Send this CONSTANT X-Forwarded-For on every request, emulating the "
        "F5/WAF collapsing all visitors to one origin IP (e.g. 10.0.0.1). "
        "Default: a DISTINCT spoofed IP per request (control: each visitor gets "
        "its own bucket, so no block is expected).",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS verification (internal hostnames / self-signed chains).",
    )
    opts = parser.parse_args()

    verify = not opts.insecure
    if opts.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    base_url = opts.base_url.rstrip("/")

    endpoints = (
        [(l, p) for l, p in ALL_ENDPOINTS if l == opts.only]
        if opts.only
        else list(SEARCH_ENDPOINTS)
    )
    mode = (
        f"COLLAPSE (constant XFF={opts.collapse_ip}, emulating the WAF)"
        if opts.collapse_ip
        else "CONTROL (distinct XFF per request, one bucket each)"
    )
    print(f"Target: {base_url}")
    print(f"Mode: {mode}")
    print(
        f"Plan: {opts.requests} anonymous searches across "
        f"{', '.join(l for l, _ in endpoints)} "
        f"(concurrency {opts.concurrency}); per-endpoint IP-keyed ceiling is "
        f"{SHARED_BUCKET_PER_HOUR}/hour, {SHARED_BUCKET_PER_DAY}/day."
    )
    print(
        "  WARNING: tripping the bucket blocks ALL anonymous TST traffic from "
        "the collapsed IP until the clock hour rolls over."
    )

    warm_up(base_url, verify)

    # --- Phase 1: collapse burst -----------------------------------------
    print(f"\n=== Phase 1: collapse burst ({opts.requests} searches) ===")
    session = requests.Session()
    session.verify = verify
    results: list[tuple[int, str, int, float]] = []
    first_block: int | None = None
    stop = threading.Event()

    with ThreadPoolExecutor(max_workers=opts.concurrency) as pool:
        futures = {}
        for n in range(opts.requests):
            if stop.is_set():
                break
            xff = opts.collapse_ip or spoofed_ip(n)
            futures[pool.submit(search_once, session, base_url, n, xff, endpoints, verify)] = n
        for future in as_completed(futures):
            n, label, status, latency = future.result()
            results.append((n, label, status, latency))
            if status in (429, 403) and first_block is None:
                first_block = n
                log(f"  [BLOCK {status}] first block at request #{n} ({label})")
                if opts.stop_on_block:
                    stop.set()
            elif status in (429, 403):
                pass  # counted in the summary
            elif status not in (200,):
                log(f"  [{status or 'transport-error'}] request #{n} ({label})")

    # --- Summary -------------------------------------------------------------
    results.sort(key=lambda r: r[0])
    statuses = Counter(status for _, _, status, _ in results)
    by_endpoint: dict[str, Counter] = {}
    for _, label, status, _ in results:
        by_endpoint.setdefault(label, Counter())[status] += 1
    latencies = sorted(lat for _, _, status, lat in results if status)

    print(f"\n--- Phase 1: {len(results)} requests ---")
    for status, count in sorted(statuses.items()):
        name = {0: "transport-error"}.get(status, str(status))
        print(f"  {name}: {count}")
    if latencies:
        p50 = statistics.median(latencies)
        p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
        print(f"  latency p50={p50 * 1000:.0f}ms p95={p95 * 1000:.0f}ms")
    print("  by endpoint:")
    for label, counter in by_endpoint.items():
        breakdown = " ".join(f"{s}:{c}" for s, c in sorted(counter.items()))
        print(f"    {label}: {breakdown}")

    # First contiguous block of 200s before the first 429 (the "free" searches).
    ok_before_block = 0
    for _, _, status, _ in results:
        if status == 200:
            ok_before_block += 1
        elif status in (429, 403):
            break

    # --- Verdict --------------------------------------------------------------
    print("\n=== Verdict ===")
    blocked = statuses.get(429, 0) + statuses.get(403, 0)
    ok = statuses.get(200, 0)
    if blocked:
        print(
            f"  [CONFIRMED] public search is rate-limit-blocked: {blocked} of "
            f"{len(results)} requests returned 429/403 (first at request "
            f"#{first_block}, after ~{ok_before_block} successful searches)."
        )
        print(
            "  Behind the WAF this bucket is SHARED across all anonymous "
            "visitors (IP collapsed to 10.0.0.1), so the listing pages stop "
            "populating for everyone once aggregate search volume crosses "
            f"{SHARED_BUCKET_PER_HOUR}/hour."
        )
        return 0
    print(
        f"  [NO BLOCK] {ok}/{len(results)} returned 200, zero 429/403. Either "
        "the hourly bucket was not exhausted (raise --requests above "
        f"{SHARED_BUCKET_PER_HOUR}), RATELIMIT is disabled (DEBUG profile / "
        "RATELIMIT_ENABLED=False), or the limiter store was reset this hour."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
