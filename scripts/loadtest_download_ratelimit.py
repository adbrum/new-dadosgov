"""Load test: prove the public DOWNLOAD/EXPORT/FEED rate-limit fix behind the F5.

Companion to scripts/loadtest_search_ratelimit.py and to the backend regression
suite udata/tests/api/test_download_ratelimit_ip_collapse.py. Where the search
script REPRODUCES the IP-collapse bug (shows 429 after 200), this one PROVES the
fix (commit "lift public download/export/feed endpoints out of the IP-keyed
rate-limit"): the endpoints that serve downloads were left under the IP-keyed
RATELIMIT_DEFAULT ("200 per hour"), which behind the F5/WAF collapses to a single
site-wide bucket (docs/infra-adc-waf-impact-ppr-prd.md §4.2) and returns 429 to
every anonymous visitor after 200 aggregated requests/hour. The fix gives each
class of endpoint its own, generously-sized, user_or_ip-keyed limit:

    RESOURCE_DOWNLOAD_LIMIT = 300/min; 6000/h  (resource "latest" + SSRF proxy)
    EXPORT_LIMIT            = 60/min;  1200/h  (CSV / RDF catalog exports)
    FEED_LIMIT              = 120/min; 2400/h  (*/recent.atom syndication feeds)

Three sub-tests, mirroring the pytest suite — all fired SEQUENTIALLY so the Nth
request maps cleanly to the Nth limiter increment (crisp threshold detection):

  A. resource-download  GET /api/1/datasets/r/<random-uuid>  (210 requests)
     A missing resource still consumes a limiter slot (the limit runs before the
     404), so random UUIDs exercise the limit without seeding data. 210 > the old
     200/h IP default and < RESOURCE_DOWNLOAD_LIMIT's 300/min, so the ONLY way a
     429 appears is the regression: the endpoint is back under the shared default.
     EXPECT: 0x429  -> CONFIRMS the download is lifted above the 200/h ceiling.

  B. export-csv         GET /api/1/site/datasets.csv          (65 requests)
     EXPECT: 0x429 in the first 60, then 429  -> CONFIRMS EXPORT_LIMIT (60/min)
     is wired, NOT the 200/h default (which would have allowed 200 before
     blocking). Blocking at ~61 is the signature of the per-endpoint fix.

  C. feed-atom          GET /api/1/datasets/recent.atom       (125 requests)
     EXPECT: 0x429 in the first 120, then 429  -> CONFIRMS FEED_LIMIT (120/min).

Taken together: A proves downloads survive past the old shared ceiling, while B
and C prove the limiter is genuinely ACTIVE on the target (not merely disabled)
and that export/feed carry their tighter per-endpoint limits rather than the
collapsing 200/h default.

The per-minute windows in B and C self-heal in <60s; A touches the separate
6000/h download bucket. NONE of these touch the 200/h anonymous default the fix
removed them from — unless the fix regressed, which is exactly what A detects.

Run through the REAL F5/WAF (gold standard — the dev host resolves the public
hostname to the F5 VIP):

    uv run --with requests python scripts/loadtest_download_ratelimit.py \
        --base-url https://ppr-dadosgov.arte.gov.pt --insecure

    # one sub-test only:
    uv run --with requests python scripts/loadtest_download_ratelimit.py \
        --base-url https://ppr-dadosgov.arte.gov.pt --insecure --only export-csv
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
import uuid
from collections import Counter

try:
    import requests
    import urllib3
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("requests not installed - run via: uv run --with requests python scripts/...")

F5_COOKIE = "cookiesession1"  # injected by the ADC / F5; evidence of WAF traversal

# Mirrored from udata/api/limits.py (the values the fix introduced).
RESOURCE_DOWNLOAD_PER_MIN = 300
EXPORT_PER_MIN = 60
FEED_PER_MIN = 120
OLD_IP_DEFAULT_PER_HOUR = 200  # RATELIMIT_DEFAULT the endpoints were lifted out of


class SubTest:
    """One endpoint exercise. `path` may contain `{uuid}` to get a fresh random
    UUID per request (resource download). `expect_block_after` is None when the
    endpoint must NEVER block within `requests` (survival proof), or an integer
    threshold N when the first N requests must pass and request N+1 must block."""

    def __init__(self, key, label, path, requests_n, expect_block_after, limit_str, proves):
        self.key = key
        self.label = label
        self.path = path
        self.requests_n = requests_n
        self.expect_block_after = expect_block_after
        self.limit_str = limit_str
        self.proves = proves


SUBTESTS = [
    SubTest(
        key="resource-download",
        label="resource download  GET /datasets/r/<uuid>",
        path="/api/1/datasets/r/{uuid}",
        requests_n=210,
        expect_block_after=None,  # must survive: 0x429 (lifted above 200/h)
        limit_str="RESOURCE_DOWNLOAD_LIMIT 300/min; 6000/h",
        proves=f"download lifted above the old {OLD_IP_DEFAULT_PER_HOUR}/h IP default",
    ),
    SubTest(
        key="export-csv",
        label="csv export         GET /site/datasets.csv",
        path="/api/1/site/datasets.csv",
        requests_n=65,
        expect_block_after=EXPORT_PER_MIN,  # 0x429 first 60, then 429
        limit_str="EXPORT_LIMIT 60/min; 1200/h",
        proves="EXPORT_LIMIT (60/min) wired, not the collapsing 200/h default",
    ),
    SubTest(
        key="feed-atom",
        label="atom feed          GET /datasets/recent.atom",
        path="/api/1/datasets/recent.atom",
        requests_n=125,
        expect_block_after=FEED_PER_MIN,  # 0x429 first 120, then 429
        limit_str="FEED_LIMIT 120/min; 2400/h",
        proves="FEED_LIMIT (120/min) wired, not the collapsing 200/h default",
    ),
]

BLOCK_STATUSES = (429, 403)


def request_url(session, base_url, st, verify):
    """Fire one GET. Returns (status, latency_s); status 0 = transport error.
    302/404 count as 'allowed' (the limiter ran and let the request through)."""
    path = st.path.format(uuid=uuid.uuid4()) if "{uuid}" in st.path else st.path
    url = f"{base_url}{path}"
    start = time.monotonic()
    try:
        # allow_redirects=False: a 302 from the CSV export means the limiter
        # passed; we don't want to follow it to the static file storage host.
        resp = session.get(
            url,
            headers={"Accept": "*/*"},
            timeout=30,
            allow_redirects=False,
        )
        return resp.status_code, time.monotonic() - start
    except requests.RequestException:
        return 0, time.monotonic() - start


def warm_up(base_url, verify):
    print("\n=== Phase 0: reachability + F5/WAF traversal ===")
    session = requests.Session()
    session.verify = verify
    try:
        resp = session.get(
            f"{base_url}/api/1/datasets/?page_size=1",
            headers={"Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"  [!] target unreachable ({exc}) - aborting")
        return False
    total = None
    try:
        total = resp.json().get("total")
    except ValueError:
        pass
    print(f"  [{resp.status_code}] /api/1/datasets/ total={total}")
    if F5_COOKIE in session.cookies:
        print(f"  F5/WAF traversal confirmed: {F5_COOKIE} cookie present")
        return True
    print(
        f"  [!] no {F5_COOKIE} cookie - not traversing the F5 (single-host run). "
        "Threshold proofs still hold; cross-visitor collapse is F5-specific."
    )
    return True


def run_subtest(session, base_url, st, verify, pace_s):
    print(f"\n=== Sub-test {st.key}: {st.label} ===")
    print(f"    limit under test: {st.limit_str}")
    expectation = (
        f"0x429 across all {st.requests_n} ({st.proves})"
        if st.expect_block_after is None
        else f"0x429 in the first {st.expect_block_after}, then 429 ({st.proves})"
    )
    print(f"    plan: {st.requests_n} sequential GETs; expect {expectation}")

    statuses = []
    latencies = []
    first_block = None
    for n in range(st.requests_n):
        status, latency = request_url(session, base_url, st, verify)
        statuses.append(status)
        if status:
            latencies.append(latency)
        if status in BLOCK_STATUSES and first_block is None:
            first_block = n  # 0-based index -> request #(n+1)
            print(f"    [BLOCK {status}] first 429/403 at request #{n + 1}")
        if status and status not in BLOCK_STATUSES and status >= 500:
            print(f"    [{status}] server error at request #{n + 1}")
        if pace_s:
            time.sleep(pace_s)

    dist = Counter(statuses)
    blocked = sum(dist.get(s, 0) for s in BLOCK_STATUSES)
    print(f"    --- {len(statuses)} requests ---")
    for s, c in sorted(dist.items()):
        print(f"      {('transport-error' if s == 0 else s)}: {c}")
    if latencies:
        lat = sorted(latencies)
        p50 = statistics.median(lat)
        p95 = lat[max(0, int(len(lat) * 0.95) - 1)]
        print(f"      latency p50={p50 * 1000:.0f}ms p95={p95 * 1000:.0f}ms")

    # --- per-sub-test verdict ---
    passed = False
    if st.expect_block_after is None:
        # Survival proof: any block is a regression to the 200/h default.
        first_idx = first_block + 1 if first_block is not None else None
        if blocked == 0:
            passed = True
            print(
                f"    [PASS] 0 of {len(statuses)} blocked -> endpoint is OUT of the "
                f"{OLD_IP_DEFAULT_PER_HOUR}/h IP default; the fix holds behind the F5."
            )
        else:
            print(
                f"    [FAIL] {blocked} blocked (first at #{first_idx}). A 429 below "
                f"the {RESOURCE_DOWNLOAD_PER_MIN}/min ceiling means the endpoint is "
                f"back under the shared {OLD_IP_DEFAULT_PER_HOUR}/h IP default."
            )
    else:
        thr = st.expect_block_after
        blocked_before = sum(1 for s in statuses[:thr] if s in BLOCK_STATUSES)
        blocked_after = sum(1 for s in statuses[thr:] if s in BLOCK_STATUSES)
        if blocked_before == 0 and blocked_after > 0:
            passed = True
            print(
                f"    [PASS] first {thr} all passed, then {blocked_after} blocked "
                f"-> the per-endpoint limit ({st.limit_str}) is active, NOT the "
                f"{OLD_IP_DEFAULT_PER_HOUR}/h default (which would allow ~200 first)."
            )
        elif blocked_before > 0:
            print(
                f"    [FAIL] {blocked_before} blocked within the first {thr} -> limit "
                "tighter than expected or a stale window leaked from a previous run."
            )
        else:
            print(
                f"    [FAIL] 0 of {len(statuses)} blocked -> the limiter did not "
                "engage (rate-limiting disabled on target? window reset?). Expected "
                f"a 429 just past request #{thr}."
            )
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base-url",
        default="https://ppr-dadosgov.arte.gov.pt",
        help="Origin to test through (default: PPR public hostname -> F5 VIP).",
    )
    parser.add_argument(
        "--only",
        choices=[st.key for st in SUBTESTS],
        default=None,
        help="Run a single sub-test instead of all three.",
    )
    parser.add_argument(
        "--pace-ms",
        type=int,
        default=0,
        help="Sleep between requests (ms). Default 0 = as fast as sequential I/O "
        "allows, which still completes each per-minute test inside one window.",
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
    subtests = [st for st in SUBTESTS if st.key == opts.only] if opts.only else SUBTESTS

    print(f"Target: {base_url}")
    print(
        "Proving the public download/export/feed rate-limit fix: each class of "
        f"endpoint must carry its own limit instead of the IP-keyed "
        f"{OLD_IP_DEFAULT_PER_HOUR}/h default that collapses site-wide behind the F5."
    )

    if not warm_up(base_url, verify):
        return 2

    session = requests.Session()
    session.verify = verify
    results = {}
    for st in subtests:
        results[st.key] = run_subtest(session, base_url, st, verify, opts.pace_ms / 1000.0)

    print("\n=== Verdict ===")
    all_passed = all(results.values())
    for st in subtests:
        print(f"  [{'PASS' if results[st.key] else 'FAIL'}] {st.key}: {st.proves}")
    if all_passed:
        print(
            "\n  [CONFIRMED] the download/export/feed fix holds on this target: "
            "downloads survive past the old 200/h ceiling and export/feed enforce "
            "their own per-endpoint limits — none collapse under the F5 IP default."
        )
        return 0
    print("\n  [NOT CONFIRMED] at least one sub-test did not behave as expected (see above).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
