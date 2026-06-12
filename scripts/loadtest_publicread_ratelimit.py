"""Load test: prove the public READ rate-limit fix (suggest/detail/reference) on PPR.

Companion to loadtest_{search,download,upload}_ratelimit.py and to the backend
regression suite udata/tests/api/test_public_read_ratelimit_ip_collapse.py
(LEDG-1901, udata-pt#92). Validates, through the REAL F5/WAF, that the anonymous
public READ endpoints were lifted out of the IP-keyed RATELIMIT_DEFAULT
("200 per hour") and now carry their own per-endpoint user_or_ip limit
(PUBLIC_SEARCH_LIMIT for typeahead, PUBLIC_READ_LIMIT for detail/reference) =
"300 per minute; 6000 per hour".

Two kinds of sub-test:
  * SURVIVAL (210 sequential GETs, expect 0x429): 210 > the old 200/h default and
    < the new 300/min ceiling, so the only way a 429 appears is the regression of
    the endpoint falling back under the shared 200/h IP default.
  * ENGAGEMENT (315 GETs, concurrent, within one minute): expect 0x429 in the
    first ~300 then 429 — proves the 300/min limit is live and keyed, not merely
    disabled.

Safe on PPR: the F5 preserves the real per-client IP (verified 2026-06-12), so
these requests trip only THIS client's per-endpoint bucket for <60s — they do
NOT exhaust a site-wide bucket. (That safety is exactly what the fix provides.)

Run from the dev box (resolves the public hostname to the F5 VIP):
    uv run --with requests python scripts/loadtest_publicread_ratelimit.py \
        --base-url https://ppr-dadosgov.arte.gov.pt --insecure --dataset-id <id>
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
    import urllib3
except ImportError:  # pragma: no cover
    sys.exit("requests not installed - run via: uv run --with requests python scripts/...")

F5_COOKIE = "cookiesession1"
OLD_IP_DEFAULT_PER_HOUR = 200
PER_MIN = 300  # PUBLIC_SEARCH_LIMIT / PUBLIC_READ_LIMIT per-minute ceiling
BLOCK = (429, 403)


def get(session, url, verify):
    start = time.monotonic()
    try:
        r = session.get(url, headers={"Accept": "application/json"}, timeout=30)
        return r.status_code, time.monotonic() - start
    except requests.RequestException:
        return 0, time.monotonic() - start


def survival(session, base, path, verify, n=OLD_IP_DEFAULT_PER_HOUR + 10):
    """Sequential GETs; expect 0x429 (endpoint lifted above the 200/h default)."""
    statuses = []
    for _ in range(n):
        s, _lat = get(session, base + path, verify)
        statuses.append(s)
    dist = Counter(statuses)
    blocked = sum(dist.get(s, 0) for s in BLOCK)
    ok = blocked == 0
    print(f"    [{'PASS' if ok else 'FAIL'}] survival {path}: {n} reqs, "
          f"{dict(sorted(dist.items()))} -> "
          + ("0x429 (lifted above 200/h)" if ok
             else f"{blocked}x blocked BELOW 300/min = regression to 200/h default"))
    return ok


def engagement(session, base, path, verify, n=PER_MIN + 15, concurrency=12):
    """Concurrent burst within one minute; expect 0x429 up to ~300 then 429."""
    results = [None] * n
    lat = []

    def fire(i):
        s, la = get(session, base + path, verify)
        results[i] = s
        if s:
            lat.append(la)

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(fire, range(n)))
    elapsed = time.monotonic() - t0
    dist = Counter(results)
    blocked = sum(dist.get(s, 0) for s in BLOCK)
    ok200 = dist.get(200, 0)
    p95 = sorted(lat)[max(0, int(len(lat) * 0.95) - 1)] if lat else 0
    # engagement is about the limiter firing once volume crosses 300/min within
    # the window; with concurrency the exact index is fuzzy, so we assert the
    # limit DID engage (>=1 block) AND a large allowed batch came through first.
    engaged = blocked > 0 and ok200 >= 250
    print(f"    [{'PASS' if engaged else 'FAIL'}] engagement {path}: {n} reqs in "
          f"{elapsed:.0f}s, {dict(sorted(dist.items()))} p95={p95*1000:.0f}ms -> "
          + ("limit engaged (300/min active, not the 200/h default)" if engaged
             else "limit did NOT engage as expected"))
    return engaged


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default="https://ppr-dadosgov.arte.gov.pt")
    ap.add_argument("--dataset-id", default=None, help="A real dataset id/slug for the detail survival test.")
    ap.add_argument("--insecure", action="store_true")
    opts = ap.parse_args()
    verify = not opts.insecure
    if opts.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    base = opts.base_url.rstrip("/")

    session = requests.Session()
    session.verify = verify

    print(f"Target: {base}")
    print("=== Phase 0: F5 traversal ===")
    r = session.get(f"{base}/api/1/datasets/?page_size=1", timeout=30)
    print(f"  /datasets/ -> {r.status_code}; F5 cookie: "
          + ("present" if F5_COOKIE in session.cookies else "ABSENT"))

    results = {}
    print("\n=== Survival (210 GETs each, expect 0x429 = lifted above 200/h) ===")
    results["suggest_datasets"] = survival(session, base, "/api/1/datasets/suggest/?q=ambiente&size=5", verify)
    results["suggest_tags"] = survival(session, base, "/api/1/tags/suggest/?q=ambiente&size=5", verify)
    results["licenses"] = survival(session, base, "/api/1/datasets/licenses/", verify)
    if opts.dataset_id:
        results["dataset_detail"] = survival(session, base, f"/api/1/datasets/{opts.dataset_id}/", verify)

    print("\n=== Engagement (burst > 300/min, expect 429 after ~300) ===")
    print("  (waiting 60s so the survival window on licenses rolls over first)")
    time.sleep(60)
    results["engagement_licenses"] = engagement(session, base, "/api/1/datasets/licenses/", verify)

    print("\n=== Verdict ===")
    for k, v in results.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
