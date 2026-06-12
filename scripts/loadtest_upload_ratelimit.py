"""Load test: prove the authenticated file-UPLOAD rate-limit fix behind the F5.

Third companion to loadtest_search_ratelimit.py and loadtest_download_ratelimit.py
and to the backend regression suite
udata/tests/api/test_upload_ratelimit_ip_collapse.py. Proves the fix "lift
authenticated file-upload endpoints out of the IP-keyed rate-limit": several
upload endpoints carried no explicit limit and fell under the IP-keyed
RATELIMIT_DEFAULT ("200 per hour"), which behind the F5/WAF collapses to a
single site-wide bucket (docs/infra-adc-waf-impact-ppr-prd.md §4.2). The fix
gives each its own user_or_ip-keyed limit:

    UPLOAD_LIMIT         = 10/min; 100/h; 500/d  (resource re-upload, images)
    CONTENT_CREATE_LIMIT = 5/min;  30/h;  100/d  (community resource re-upload)

Method — the safe, credential-free way that also proves the limiter sits in
front of auth: fire requests ANONYMOUSLY. The limiter decorator wraps the view
and runs BEFORE @api.secure, so each anonymous POST consumes a limiter slot
(keyed by IP via the user_or_ip fallback) and returns 401 until the
per-endpoint ceiling is crossed, then 429. The signature of the fix is a 429 at
the per-endpoint threshold (11th / 6th request) — NOT at ~200, which the
collapsing IP-keyed default would have allowed.

Why this is safe to run on PPR (unlike reproducing the *bug*): with the fix
deployed, each endpoint has its OWN per-minute bucket, separate from the
anonymous 200/h default. Tripping it blocks only that endpoint, for that IP,
for <60s — it does NOT exhaust the site-wide anonymous bucket. (Running this
against an UNFIXED build WOULD be harmful: the requests would fall on the 200/h
default and block all anonymous traffic site-wide for the hour. Don't.)

Run through the real F5 (dev host resolves the public hostname to the F5 VIP):

    uv run --with requests python scripts/loadtest_upload_ratelimit.py \
        --base-url https://ppr-dadosgov.arte.gov.pt --insecure
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

F5_COOKIE = "cookiesession1"
OLD_IP_DEFAULT_PER_HOUR = 200
UPLOAD_PER_MIN = 10  # UPLOAD_LIMIT
CONTENT_CREATE_PER_MIN = 5  # CONTENT_CREATE_LIMIT
BLOCK_STATUSES = (429, 403)


class SubTest:
    def __init__(self, key, label, build_path, threshold, limit_str):
        self.key = key
        self.label = label
        self.build_path = build_path  # fn(ids) -> path str, or None if id missing
        self.threshold = threshold
        self.limit_str = limit_str


# Each endpoint's path is built from real ids fetched in phase 0. The resource
# re-upload only needs a real dataset (the <uuid:rid> segment is a format-only
# converter, so a random UUID resolves without a DB lookup).
SUBTESTS = [
    SubTest(
        "upload_dataset_resource",
        "replace resource file  POST /datasets/<d>/resources/<rid>/upload/",
        lambda ids: f"/api/1/datasets/{ids['dataset']}/resources/{uuid.uuid4()}/upload/"
        if ids.get("dataset")
        else None,
        UPLOAD_PER_MIN,
        "UPLOAD_LIMIT 10/min",
    ),
    SubTest(
        "reuse_image",
        "reuse image            POST /reuses/<reuse>/image/",
        lambda ids: f"/api/1/reuses/{ids['reuse']}/image/" if ids.get("reuse") else None,
        UPLOAD_PER_MIN,
        "UPLOAD_LIMIT 10/min",
    ),
    SubTest(
        "post_image",
        "post image             POST /posts/<post>/image/",
        lambda ids: f"/api/1/posts/{ids['post']}/image/" if ids.get("post") else None,
        UPLOAD_PER_MIN,
        "UPLOAD_LIMIT 10/min",
    ),
    SubTest(
        "user_avatar",
        "user avatar            POST /users/<user>/avatar/",
        lambda ids: f"/api/1/users/{ids['user']}/avatar/" if ids.get("user") else None,
        UPLOAD_PER_MIN,
        "UPLOAD_LIMIT 10/min",
    ),
    SubTest(
        "upload_community_resource",
        "re-upload commres      POST /datasets/community_resources/<crid>/upload/",
        lambda ids: f"/api/1/datasets/community_resources/{ids['commres']}/upload/"
        if ids.get("commres")
        else None,
        CONTENT_CREATE_PER_MIN,
        "CONTENT_CREATE_LIMIT 5/min",
    ),
]


def fetch_ids(base_url, verify):
    """Fetch one real id per object type from the public API."""
    session = requests.Session()
    session.verify = verify
    ids = {}

    def first_id(path):
        try:
            r = session.get(f"{base_url}{path}", headers={"Accept": "application/json"}, timeout=30)
            data = r.json().get("data") or []
            return data[0]["id"] if data else None
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return None

    ids["dataset"] = first_id("/api/1/datasets/?page_size=1")
    ids["reuse"] = first_id("/api/1/reuses/?page_size=1")
    ids["post"] = first_id("/api/1/posts/?page_size=1")
    ids["user"] = first_id("/api/1/users/?page_size=1")
    ids["commres"] = first_id("/api/1/datasets/community_resources/?page_size=1")
    traversed = F5_COOKIE in session.cookies
    return ids, traversed


def run_subtest(session, base_url, st, ids, verify, pace_s):
    print(f"\n=== Sub-test {st.key}: {st.label} ===")
    print(f"    limit under test: {st.limit_str}")
    path = st.build_path(ids)
    if not path:
        print("    [SKIP] no real object id available for this endpoint's converter "
              "(covered by the pytest regression suite instead).")
        return None

    n = st.threshold + 3
    statuses = []
    latencies = []
    first_block = None
    for i in range(n):
        start = time.monotonic()
        try:
            resp = session.post(
                f"{base_url}{path}",
                headers={"Accept": "*/*"},
                timeout=30,
                allow_redirects=False,
            )
            status = resp.status_code
        except requests.RequestException:
            status = 0
        statuses.append(status)
        if status:
            latencies.append(time.monotonic() - start)
        if status in BLOCK_STATUSES and first_block is None:
            first_block = i + 1
        if pace_s:
            time.sleep(pace_s)

    dist = Counter(statuses)
    print(f"    plan: {n} anonymous POSTs; expect 0x429 in first {st.threshold}, then 429")
    print(f"    statuses: {dict(sorted(dist.items()))}"
          + (f"  (first 429 at #{first_block})" if first_block else ""))
    if latencies:
        lat = sorted(latencies)
        print(f"    latency p50={statistics.median(lat) * 1000:.0f}ms "
              f"p95={lat[max(0, int(len(lat) * 0.95) - 1)] * 1000:.0f}ms")

    thr = st.threshold
    blocked_before = [s for s in statuses[:thr] if s in BLOCK_STATUSES]
    blocked_after = [s for s in statuses[thr:] if s in BLOCK_STATUSES]
    if not blocked_before and blocked_after:
        print(f"    [PASS] first {thr} passed, then 429 -> per-endpoint limit "
              f"({st.limit_str}) active, NOT the {OLD_IP_DEFAULT_PER_HOUR}/h default.")
        return True
    if blocked_before:
        print(f"    [FAIL] blocked within first {thr} (stale per-minute window? "
              "wait 60s and re-run) or limit tighter than expected.")
        return False
    print(f"    [FAIL] no 429 past #{thr} -> endpoint unlimited or still under the "
          f"collapsing {OLD_IP_DEFAULT_PER_HOUR}/h IP default.")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="https://ppr-dadosgov.arte.gov.pt")
    parser.add_argument("--only", choices=[st.key for st in SUBTESTS], default=None)
    parser.add_argument("--pace-ms", type=int, default=0)
    parser.add_argument("--insecure", action="store_true")
    opts = parser.parse_args()

    verify = not opts.insecure
    if opts.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    base_url = opts.base_url.rstrip("/")
    subtests = [st for st in SUBTESTS if st.key == opts.only] if opts.only else SUBTESTS

    print(f"Target: {base_url}")
    print("Proving the authenticated file-upload rate-limit fix: each upload endpoint "
          f"must carry its own user_or_ip limit, not the IP-keyed {OLD_IP_DEFAULT_PER_HOUR}/h "
          "default that collapses site-wide behind the F5.")

    print("\n=== Phase 0: fetch real ids + F5/WAF traversal ===")
    ids, traversed = fetch_ids(base_url, verify)
    for k, v in ids.items():
        print(f"    {k}: {v or 'NOT AVAILABLE'}")
    print(f"    F5/WAF traversal: {'confirmed (' + F5_COOKIE + ')' if traversed else 'NOT confirmed'}")

    session = requests.Session()
    session.verify = verify
    results = {}
    for st in subtests:
        results[st.key] = run_subtest(session, base_url, st, ids, verify, opts.pace_ms / 1000.0)

    print("\n=== Verdict ===")
    tested = {k: v for k, v in results.items() if v is not None}
    for st in subtests:
        v = results[st.key]
        tag = "SKIP" if v is None else ("PASS" if v else "FAIL")
        print(f"  [{tag}] {st.key}")
    if tested and all(tested.values()):
        print(f"\n  [CONFIRMED] all {len(tested)} tested upload endpoints enforce their own "
              "per-endpoint limit behind the F5 — none collapse under the IP default.")
        return 0
    print("\n  [NOT CONFIRMED] at least one tested sub-test did not behave as expected.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
