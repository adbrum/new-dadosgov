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

DOWNLOAD/EXPORT/FEED coverage (amagovpt/udata-pt#90): the same IP-collapse
exposure applied to the endpoints that serve downloads — the resource "latest"
download, the CSV/RDF catalog exports and the Atom feeds — which also had no
per-endpoint limit. Use `--group export|feed|listing` (round-robin) or `--only
<label>` to target them. After the fix each carries its own user_or_ip-keyed
ceiling (RESOURCE_DOWNLOAD_LIMIT 300/min;6000/h, EXPORT_LIMIT 60/min;1200/h,
FEED_LIMIT 120/min;2400/h), so the per-minute ceiling is what a burst trips
first — set --requests just past it (e.g. ~70 for export, ~130 for feed).

Usage (from repo root):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url https://10.55.37.38 --insecure

    # stop as soon as blocking is demonstrated (don't waste the whole bucket):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url https://10.55.37.38 --insecure --stop-on-block

    # CSV export collapse behind the WAF (EXPORT_LIMIT 60/min -> block ~#60):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url https://10.55.37.38 --insecure \
        --only site-datasets-csv --collapse-ip 10.0.0.1 --requests 70

    # Atom feed group, round-robin (FEED_LIMIT 120/min):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url https://10.55.37.38 --insecure \
        --group feed --collapse-ip 10.0.0.1 --requests 520

    # resource download (random UUID still trips the limiter before the 404):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url https://10.55.37.38 --insecure \
        --only resource-download --resource-id <uuid> --collapse-ip 10.0.0.1

    # dry-run against a local stack (no WAF, single host -> still collapses):
    uv run --with requests python scripts/loadtest_search_ratelimit.py \
        --base-url http://localhost:3000
"""

from __future__ import annotations

import argparse
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

# Public DOWNLOAD/EXPORT endpoints (amagovpt/udata-pt#90). Same IP-collapse
# exposure as search: anonymous GETs that, before the fix, had no per-endpoint
# limit and fell under the IP-keyed RATELIMIT_DEFAULT, collapsing to one shared
# 200/hour bucket behind the F5. After the fix each carries its own
# user_or_ip-keyed ceiling EXPORT_LIMIT = "60 per minute; 1200 per hour"
# (udata/api/limits.py). CSV/RDF dumps are heavy to generate, so the per-minute
# ceiling (60) is what a burst trips first. Target with --group export or
# --only <label>.
EXPORT_ENDPOINTS = [
    ("site-datasets-csv", "/api/1/site/datasets.csv"),
    ("site-organizations-csv", "/api/1/site/organizations.csv"),
    ("site-reuses-csv", "/api/1/site/reuses.csv"),
    ("site-catalog-rdf", "/api/1/site/catalog.json"),
]

# Public FEED endpoints (amagovpt/udata-pt#90). Atom syndication feeds polled by
# aggregators; same pre-fix IP-collapse exposure. After the fix each carries
# FEED_LIMIT = "120 per minute; 2400 per hour". Target with --group feed.
FEED_ENDPOINTS = [
    ("datasets-feed", "/api/1/datasets/recent.atom"),
    ("reuses-feed", "/api/1/reuses/recent.atom"),
    ("dataservices-feed", "/api/1/dataservices/recent.atom"),
    ("posts-feed", "/api/1/posts/recent.atom"),
]

# The resource "latest" download. Needs a concrete resource UUID, so it is not
# part of any default group; target it with `--only resource-download
# --resource-id <uuid>`. After the fix it carries RESOURCE_DOWNLOAD_LIMIT =
# "300 per minute; 6000 per hour" (the most frequent public action, not
# cacheable). A missing UUID still consumes a limiter slot (the limit runs
# before the 404), so even a random id exercises the ceiling.
RESOURCE_DOWNLOAD_LABEL = "resource-download"
RESOURCE_DOWNLOAD_PATH_TMPL = "/api/1/datasets/r/{resource_id}"

# Endpoint groups selectable via --group (round-robin within the group).
GROUPS = {
    "search": SEARCH_ENDPOINTS,
    "listing": SITE_LISTING_ENDPOINTS,
    "export": EXPORT_ENDPOINTS,
    "feed": FEED_ENDPOINTS,
}

ALL_ENDPOINTS = (
    SEARCH_ENDPOINTS
    + SITE_LISTING_ENDPOINTS
    + EXPORT_ENDPOINTS
    + FEED_ENDPOINTS
    + [(RESOURCE_DOWNLOAD_LABEL, RESOURCE_DOWNLOAD_PATH_TMPL)]
)

# Labels whose URL carries a real search query (q + pagination); everything else
# (exports, feeds, downloads) just gets a cache-buster so no upstream cache
# absorbs the burst. The limiter keys on IP, not on the query, either way.
SEARCH_LIKE_LABELS = {label for label, _ in SEARCH_ENDPOINTS + SITE_LISTING_ENDPOINTS}

# Post-fix per-endpoint ceilings, for report expectations only — the limiter in
# udata/api/limits.py is the source of truth. Maps label -> (constant name,
# per-minute, per-hour). Unmapped labels fall back to the IP-keyed default.
POSTFIX_LIMIT: dict[str, tuple[str, int, int]] = {
    **{label: ("PUBLIC_SEARCH_LIMIT", 300, 6000) for label in SEARCH_LIKE_LABELS},
    **{label: ("EXPORT_LIMIT", 60, 1200) for label, _ in EXPORT_ENDPOINTS},
    **{label: ("FEED_LIMIT", 120, 2400) for label, _ in FEED_ENDPOINTS},
    RESOURCE_DOWNLOAD_LABEL: ("RESOURCE_DOWNLOAD_LIMIT", 300, 6000),
}

# Rotating query terms so requests look like real distinct searches rather than
# one cached query. Content is irrelevant to the rate limiter (it keys on IP),
# but varied queries also defeat any per-query response caching on the way.
QUERIES = [
    "ambiente",
    "saude",
    "educacao",
    "transportes",
    "economia",
    "energia",
    "turismo",
    "cultura",
    "agricultura",
    "justica",
    "habitacao",
    "clima",
    "covid",
    "orcamento",
    "mobilidade",
    "censos",
    "florestas",
    "agua",
    "emprego",
    "demografia",
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


def build_url(base_url: str, label: str, path: str, n: int) -> str:
    """Build the request URL for endpoint `label`.

    Search/listing endpoints carry a rotating real query + pagination (so tiny
    result sets don't 404 and any per-query cache is defeated). Exports, feeds
    and downloads instead get a `_=<n>` cache-buster so no upstream cache
    absorbs the burst; the rate limiter keys on IP regardless of the query."""
    if label in SEARCH_LIKE_LABELS:
        query = QUERIES[n % len(QUERIES)]
        return f"{base_url}{path}?q={query}&page=1&page_size=20"
    sep = "&" if "?" in path else "?"
    return f"{base_url}{path}{sep}_={n}"


def search_once(
    session: requests.Session,
    base_url: str,
    n: int,
    xff: str,
    endpoints: list[tuple[str, str]],
    verify: bool,
) -> tuple[int, str, int, float]:
    """One anonymous request. Returns (n, endpoint_label, status, latency_s).
    status 0 = transport error.

    `xff` is the X-Forwarded-For sent. A DISTINCT value per request (control)
    keys each call to its own bucket -> no block. A CONSTANT value (collapse
    mode) emulates the F5/WAF presenting one origin IP -> shared bucket -> 429.
    The limiter counts every request regardless of page or status, so 404s from
    tiny result sets or a missing resource id still exercise the ceiling."""
    label, path = endpoints[n % len(endpoints)]
    url = build_url(base_url, label, path, n)
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


def warm_up(base_url: str, verify: bool, endpoints: list[tuple[str, str]]) -> bool:
    """Phase 0: one request per target endpoint; assert reachable + report WAF
    cookie. Returns True if traffic appears to traverse the emulated WAF.

    Tolerant across endpoint kinds: search/listing return JSON with a `total`;
    exports stream CSV/RDF and feeds return Atom XML (no `total`); a
    resource-download with a random UUID returns 404 but still proves the route
    is wired. Any non-5xx, non-0 status counts as reachable."""
    print("\n=== Phase 0: reachability + WAF traversal ===")
    session = requests.Session()
    session.verify = verify
    traversed = False
    for label, path in endpoints:
        url = build_url(base_url, label, path, 0)
        try:
            resp = session.get(url, headers={"Accept": "application/json"}, timeout=30)
        except requests.RequestException as exc:
            print(f"  [!] {label}: request failed ({exc})")
            return False
        total = None
        try:
            total = resp.json().get("total")
        except (ValueError, AttributeError):
            pass
        suffix = f": total={total}" if total is not None else ""
        print(f"  [{resp.status_code}] {label}{suffix}")
        # Reachable = the app answered. Search/listing must be 200; exports/feeds
        # are 200 too; resource-download is allowed 404 (random UUID). Only a
        # 5xx or transport error aborts.
        if resp.status_code >= 500 or resp.status_code == 0:
            print(f"  [!] {label} returned {resp.status_code} on a single request - aborting")
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
        "block. With --only, enough requests to one endpoint trip its bucket.",
    )
    parser.add_argument(
        "--group",
        choices=sorted(GROUPS),
        default="search",
        help="Endpoint group to round-robin when --only is not given "
        "(default: search). 'export' = CSV/RDF dumps, 'feed' = Atom feeds, "
        "'listing' = SSR /site/*-listing/. Ignored when --only is set.",
    )
    parser.add_argument(
        "--resource-id",
        default=None,
        metavar="UUID",
        help="Resource UUID for `--only resource-download`. A random/missing id "
        "still trips the limit (the limiter runs before the 404), but a real id "
        "exercises the full download path.",
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

    if opts.only:
        label, path = next((lbl, p) for lbl, p in ALL_ENDPOINTS if lbl == opts.only)
        if label == RESOURCE_DOWNLOAD_LABEL:
            # Default to the all-zeros UUID; a missing resource still trips the
            # limit (the limiter runs before the 404).
            rid = opts.resource_id or "00000000-0000-0000-0000-000000000000"
            path = RESOURCE_DOWNLOAD_PATH_TMPL.format(resource_id=rid)
        endpoints = [(label, path)]
    else:
        endpoints = list(GROUPS[opts.group])

    # Expected post-fix ceiling for the targeted endpoints, for report context.
    limit_names = {POSTFIX_LIMIT[lbl][0] for lbl, _ in endpoints if lbl in POSTFIX_LIMIT}
    per_min = sorted({POSTFIX_LIMIT[lbl][1] for lbl, _ in endpoints if lbl in POSTFIX_LIMIT})
    per_hour = sorted({POSTFIX_LIMIT[lbl][2] for lbl, _ in endpoints if lbl in POSTFIX_LIMIT})
    if limit_names:
        ceiling_desc = (
            f"post-fix {'/'.join(sorted(limit_names))} ceiling "
            f"{'/'.join(map(str, per_min))} per minute, "
            f"{'/'.join(map(str, per_hour))} per hour (user_or_ip-keyed)"
        )
    else:
        ceiling_desc = (
            f"IP-keyed default {SHARED_BUCKET_PER_HOUR}/hour, "
            f"{SHARED_BUCKET_PER_DAY}/day (pre-fix exposure)"
        )

    mode = (
        f"COLLAPSE (constant XFF={opts.collapse_ip}, emulating the WAF)"
        if opts.collapse_ip
        else "CONTROL (distinct XFF per request, one bucket each)"
    )
    print(f"Target: {base_url}")
    print(f"Mode: {mode}")
    print(
        f"Plan: {opts.requests} anonymous requests across "
        f"{', '.join(lbl for lbl, _ in endpoints)} "
        f"(concurrency {opts.concurrency}); {ceiling_desc}."
    )
    print(
        "  WARNING: tripping the bucket blocks ALL anonymous TST traffic from "
        "the collapsed IP until the window rolls over."
    )

    warm_up(base_url, verify, endpoints)

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
    targeted = ", ".join(sorted({lbl for lbl, _ in endpoints}))
    if blocked:
        print(
            f"  [CONFIRMED] {targeted} is rate-limit-blocked: {blocked} of "
            f"{len(results)} requests returned 429/403 (first at request "
            f"#{first_block}, after ~{ok_before_block} successful requests)."
        )
        if opts.collapse_ip:
            print(
                "  Behind the WAF this bucket is SHARED across all anonymous "
                f"visitors (IP collapsed to {opts.collapse_ip}), so the endpoint "
                "stops serving for everyone once aggregate volume crosses the "
                "ceiling — the exact pre-fix failure mode. Confirm the post-fix "
                "ceiling is the generous user_or_ip one above (not the IP-keyed "
                f"{SHARED_BUCKET_PER_HOUR}/hour default)."
            )
        else:
            print(
                "  NOTE: this is a CONTROL run (distinct XFF per request). A "
                "block here means the limit triggered on a single spoofed-IP "
                "stream — re-run with --collapse-ip to emulate the WAF, or raise "
                "the per-endpoint ceiling if this is legitimate volume."
            )
        return 0
    print(
        f"  [NO BLOCK] {ok}/{len(results)} returned 200, zero 429/403. Either "
        "the window was not exhausted (raise --requests above the per-minute "
        "ceiling reported above), RATELIMIT is disabled (DEBUG profile / "
        "RATELIMIT_ENABLED=False), or the limiter store was reset this window."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
