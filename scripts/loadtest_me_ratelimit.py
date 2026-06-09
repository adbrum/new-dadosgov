"""Load test: validate the per-user rate-limit fix on GET /api/1/me/ behind the F5.

Context (docs/infra-adc-waf-impact-ppr-prd.md, incident 4.2): behind the F5 +
proxy chain the backend used to see every user with the same origin IP, so the
IP-keyed RATELIMIT_DEFAULT ("1000/day; 200/hour") collapsed all users into one
bucket on /api/1/me/ -> 429 -> the frontend read it as "session expired" ->
random mass logouts in PRD. The fix keys the limit per authenticated user
(IDENTITY_READ_LIMIT = "60/min; 1200/hour", key_func=user_or_ip) and forwards
X-Forwarded-For through the Next.js proxy.

PPR never reproduced the incident because its traffic is too low to exhaust the
shared bucket, so this script generates the missing load:

  Phase 1 (login)    N users authenticate via the frontend `POST /login` route.
                     All sessions originate from this machine -> one origin IP,
                     exactly the production collapse condition, through the
                     real F5 (the injected `cookiesession1` cookie is asserted
                     as evidence the appliance was traversed).
  Phase 2 (collapse) All users poll `GET /me` concurrently. Aggregate volume is
                     sized well above the old 200/hour shared bucket while each
                     user stays below the new 60/min per-user limit.
                     Old code: ~aggregate-200 requests answer 429.
                     Fixed code: zero 429.
  Phase 3 (control)  One dedicated user fires an unpaced burst above 60/min and
                     MUST receive 429s -> proves the limiter is active and
                     keyed per user, not merely disabled.

PASS = phase 2 has zero 429 AND phase 3 sees at least one 429.

Usage (from repo root):
    export LOADTEST_PASSWORD='<seed users password>'
    uv run --with requests python scripts/loadtest_me_ratelimit.py \
        --base-url https://ppr-dadosgov.arte.gov.pt --insecure

    # PRD: only 2 accounts are registered, so use the prd pool. Credentials are
    # taken from PRD_PASSWORD_1 / PRD_PASSWORD_2 (falling back to the literals in
    # PRD_ACCOUNTS). The prd defaults size phase 2 to push the aggregate above
    # the old 200/hour bucket with just 2 users, and the phase-3 control reuses
    # one burst user (no spare account), so that account gets 429-flagged.
    export PRD_PASSWORD_1='<adbrum password>'
    export PRD_PASSWORD_2='<dados@ama.gov.pt password>'
    uv run --with requests python scripts/loadtest_me_ratelimit.py \
        --accounts prd --base-url https://dados.gov.pt --insecure

    # dry-run against a local stack:
    uv run --with requests python scripts/loadtest_me_ratelimit.py \
        --base-url http://localhost:3000

Budget note: loadtest/seed phase 2 defaults (12 users x 30 req over 60s) total
360 requests, ~30/min per user; phase 3 adds 130 requests for one extra user.
The prd pool defaults to 2 users x 120 req over 180s = 240 aggregate (~40/min
per user, above the old 200/hour bucket but below the new 60/min per-user
limit). Logins and other non-/me traffic from this machine stay far below the
global 200/hour IP bucket, so the test does not rate-limit itself.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
    import urllib3
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("requests not installed - run via: uv run --with requests python scripts/...")

# Dedicated load-test accounts (created via `udata user create`, non-admin).
# Preferred: they carry no real data and the phase-3 control can 429-flag one
# freely. Select with --accounts loadtest.
LOADTEST_EMAILS = [f"loadtest{i:02d}@dados.gov.pt" for i in range(1, 14)]

# Same accounts as scripts/seed_admin_users.py (password via LOADTEST_PASSWORD).
SEED_EMAILS = [
    "vitor.almeida@lbc-digital.com",
    "sergio.carvalho@lbc-digital.com",
    "kelman.santos@lbc-global.com",
    "maryelem.silva@lbc-global.com",
    "jonathan.almeida@lbc-digital.com",
    "marcos.ramos@lbc-digital.com",
    "valentim.pinto@lbc-global.com",
    "camila.manique@lbc-global.com",
    "erica.gameiro@lbc-global.com",
    "miguel.peneda@lbc-global.com",
    "laura.pereira@lbc-digital.com",
    "pedro.lima@lbc-digital.com",
    "joao.barradas@lbc-digital.com",
    "matheus.teixeira@lbc-digital.com",
    "ana.carvalho@babelgroup.com",
    "ines.correia@babelgroup.com",
    "joao.conceicao@babelgroup.com",
    "dados.abertos.l12@babelgroup.com",
    "joao.curado@ext.babelgroup.com",
]

# The only accounts registered in PRD (per-account passwords, since they differ
# and are not the seed password). Prefer supplying them via env vars
# (PRD_PASSWORD_1 / PRD_PASSWORD_2) over committing real credentials; the
# literals below are fallbacks for ad-hoc local runs only. Select with
# --accounts prd. NOTE: with only 2 accounts the phase-3 control reuses one of
# the burst users (there is no spare account), so that account WILL be
# 429-flagged by the negative control.
PRD_ACCOUNTS: list[tuple[str, str]] = [
    ("adbrum@outlook.com", os.environ.get("PRD_PASSWORD_1", "ArVl261292ArVl+")),
    ("dados@ama.gov.pt", os.environ.get("PRD_PASSWORD_2", "fJTrGVW!UQP4cmr")),
]


def build_pool(name: str) -> list[tuple[str, str]]:
    """Return the (email, password) pairs for the requested account pool."""
    if name == "prd":
        return list(PRD_ACCOUNTS)
    seed_pw = os.environ.get("LOADTEST_PASSWORD", "")
    emails = LOADTEST_EMAILS if name == "loadtest" else SEED_EMAILS
    return [(email, seed_pw) for email in emails]

# Limits mirrored from backend/udata/api/limits.py and udata/settings.py.
PER_USER_LIMIT_PER_MIN = 60  # IDENTITY_READ_LIMIT "60 per minute"
OLD_SHARED_BUCKET_PER_HOUR = 200  # RATELIMIT_DEFAULT "200 per hour" (IP-keyed)

F5_COOKIE = "cookiesession1"  # injected by the ADC; evidence of F5 traversal

print_lock = threading.Lock()


def log(msg: str) -> None:
    with print_lock:
        print(msg, flush=True)


def login(base_url: str, email: str, password: str, verify: bool) -> requests.Session | None:
    """Authenticate via the frontend /login route handler; return a session
    carrying the auth cookies, or None on failure."""
    session = requests.Session()
    session.verify = verify
    try:
        resp = session.post(
            f"{base_url}/login",
            data={"email": email, "password": password},
            headers={"Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        log(f"  [!] {email}: login request failed ({exc})")
        return None
    if resp.status_code != 200:
        detail = ""
        try:
            detail = resp.json().get("message", "")
        except ValueError:
            pass
        log(f"  [!] {email}: login -> {resp.status_code} {detail}")
        return None
    return session


def poll_me(session: requests.Session, base_url: str) -> tuple[int, float]:
    """Single GET /me; returns (status, latency_seconds). 0 = transport error."""
    start = time.monotonic()
    try:
        resp = session.get(
            f"{base_url}/me",
            headers={"Accept": "application/json"},
            timeout=30,
        )
        return resp.status_code, time.monotonic() - start
    except requests.RequestException:
        return 0, time.monotonic() - start


def run_user_burst(
    session: requests.Session,
    base_url: str,
    email: str,
    n_requests: int,
    duration: float,
    results: list,
) -> None:
    """Spread n_requests evenly across `duration` seconds (paced burst)."""
    interval = duration / n_requests if n_requests else 0
    for i in range(n_requests):
        target = time.monotonic() + interval
        status, latency = poll_me(session, base_url)
        results.append((email, status, latency))
        if status == 429:
            log(f"  [429] {email} on request {i + 1}/{n_requests}")
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)


def summarize(label: str, results: list) -> Counter:
    statuses = Counter(status for _, status, _ in results)
    latencies = sorted(lat for _, status, lat in results if status)
    print(f"\n--- {label}: {len(results)} requests ---")
    for status, count in sorted(statuses.items()):
        name = {0: "transport-error"}.get(status, str(status))
        print(f"  {name}: {count}")
    if latencies:
        p50 = statistics.median(latencies)
        p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
        print(f"  latency p50={p50 * 1000:.0f}ms p95={p95 * 1000:.0f}ms")
    per_user_429 = Counter(email for email, status, _ in results if status == 429)
    if per_user_429:
        print("  429 by user:")
        for email, count in per_user_429.most_common():
            print(f"    {email}: {count}")
    return statuses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base-url",
        default="https://dados.gov.pt",
        help="Frontend origin to test through (default: PPR via the F5 VIP).",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=None,
        help="Concurrent users in phase 2 (default: pool-specific).",
    )
    parser.add_argument(
        "--requests-per-user",
        type=int,
        default=None,
        help="Paced GET /me calls per user in phase 2 (keep below 60/min each; "
        "default: pool-specific).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Window in seconds over which each user's requests are spread "
        "(default: pool-specific).",
    )
    parser.add_argument(
        "--control-requests",
        type=int,
        default=None,
        help="Unpaced burst size for the phase-3 negative control "
        "(>60 to trip the per-user limit even across several workers; "
        "default: pool-specific).",
    )
    parser.add_argument(
        "--login-interval",
        type=float,
        default=13.0,
        help="Seconds between phase-1 logins. The backend shares a "
        "'5 per minute' IP-keyed bucket across auth endpoints "
        "(udata/auth/views.py scope='auth') and all test logins come from "
        "this machine, so anything faster than ~12s/login gets 429'd.",
    )
    parser.add_argument(
        "--accounts",
        choices=["loadtest", "seed", "prd"],
        default="loadtest",
        help="Account pool: dedicated loadtestNN users (default), the "
        "seed_admin_users.py accounts, or the 2 PRD-registered accounts (prd).",
    )
    parser.add_argument(
        "--skip-control",
        action="store_true",
        help="Skip phase 3 (e.g. to avoid 429-flagging a seed account).",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS verification (internal hostnames/self-signed chains).",
    )
    opts = parser.parse_args()

    # Pool-specific sizing defaults. The loadtest/seed pools have ~13-19 accounts
    # so a single 60s burst can clear the old 200/hour shared bucket. The prd
    # pool has only 2 accounts, so each user must send more requests over a
    # longer window to push the aggregate above 200 while staying under 60/min.
    POOL_DEFAULTS = {
        "loadtest": dict(users=12, requests_per_user=30, duration=60.0, control_requests=130),
        "seed": dict(users=12, requests_per_user=30, duration=60.0, control_requests=130),
        "prd": dict(users=2, requests_per_user=120, duration=180.0, control_requests=130),
    }
    defaults = POOL_DEFAULTS[opts.accounts]
    if opts.users is None:
        opts.users = defaults["users"]
    if opts.requests_per_user is None:
        opts.requests_per_user = defaults["requests_per_user"]
    if opts.duration is None:
        opts.duration = defaults["duration"]
    if opts.control_requests is None:
        opts.control_requests = defaults["control_requests"]

    pool = build_pool(opts.accounts)
    if opts.accounts != "prd" and not os.environ.get("LOADTEST_PASSWORD"):
        print("LOADTEST_PASSWORD not set (the seed_admin_users.py password).", file=sys.stderr)
        return 2
    missing_pw = [email for email, pw in pool[: opts.users + 1] if not pw]
    if missing_pw:
        print(f"No password for account(s): {', '.join(missing_pw)}.", file=sys.stderr)
        return 2

    # With a dedicated control we need users+1 accounts. If the pool is too small
    # (e.g. the 2-account prd pool), reuse one burst user as the control instead
    # of aborting; phase 3 runs after phase 2 so the burst metrics stay clean,
    # but that account ends up 429-flagged by the negative control.
    reuse_control = False
    needed = opts.users + (0 if opts.skip_control else 1)
    if needed > len(pool):
        if opts.skip_control or len(pool) < 2:
            print(f"Need {needed} accounts but only {len(pool)} available.", file=sys.stderr)
            return 2
        reuse_control = True
        needed = opts.users
        print(
            f"  [i] only {len(pool)} accounts for {opts.users} burst users - "
            "phase-3 control will reuse one burst user (it will be 429-flagged)."
        )

    verify = not opts.insecure
    if opts.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = opts.base_url.rstrip("/")
    rate_per_user = opts.requests_per_user / (opts.duration / 60)
    aggregate = opts.users * opts.requests_per_user
    print(f"Target: {base_url}")
    print(
        f"Phase 2 plan: {opts.users} users x {opts.requests_per_user} req "
        f"over {opts.duration:.0f}s = {aggregate} aggregate "
        f"(~{rate_per_user:.0f}/min per user)"
    )
    if rate_per_user >= PER_USER_LIMIT_PER_MIN:
        print(
            f"Per-user pace {rate_per_user:.0f}/min >= {PER_USER_LIMIT_PER_MIN}/min limit - "
            "phase 2 would 429 even with the fix. Lower --requests-per-user "
            "or raise --duration.",
            file=sys.stderr,
        )
        return 2
    if aggregate <= OLD_SHARED_BUCKET_PER_HOUR:
        print(
            f"Aggregate {aggregate} <= old shared bucket "
            f"({OLD_SHARED_BUCKET_PER_HOUR}/hour) - the test would not have "
            "tripped the pre-fix limiter, so passing proves nothing. "
            "Raise --users or --requests-per-user.",
            file=sys.stderr,
        )
        return 2

    # --- Phase 1: login ---------------------------------------------------
    print(f"\n=== Phase 1: logging in {needed} users ({opts.accounts} pool) ===")
    credentials = pool[:needed]
    emails = [email for email, _ in credentials]
    print(f"  (paced at 1 login / {opts.login_interval:.0f}s - shared 5/min auth bucket)")
    sessions: dict[str, requests.Session] = {}
    for i, (email, account_pw) in enumerate(credentials):  # serial+paced: under the auth bucket
        if i:
            time.sleep(opts.login_interval)
        session = login(base_url, email, account_pw, verify)
        if session:
            sessions[email] = session
            log(f"  [+] {email}")

    if len(sessions) < 2:
        print("Fewer than 2 users authenticated - aborting.", file=sys.stderr)
        return 1
    if len(sessions) < needed:
        print(f"  [!] only {len(sessions)}/{needed} logins OK - continuing degraded")

    through_f5 = sum(1 for s in sessions.values() if F5_COOKIE in s.cookies)
    if through_f5:
        print(f"  F5 traversal confirmed: {F5_COOKIE} present on {through_f5} sessions")
    else:
        print(f"  [!] no {F5_COOKIE} cookie seen - traffic may NOT be passing the F5/WAF")

    control_email = None if opts.skip_control else emails[-1]
    control_login_failed = bool(control_email) and control_email not in sessions
    if control_login_failed:
        print(f"  [!] control account {control_email} failed login - phase 3 will not run")
        control_email = None
    # When reusing a burst user as the control, keep it in the phase-2 set;
    # otherwise the control account is excluded from the collapse burst.
    if reuse_control:
        burst_users = list(sessions)
    else:
        burst_users = [e for e in sessions if e != control_email]

    # --- Phase 2: collapse burst -------------------------------------------
    actual_aggregate = len(burst_users) * opts.requests_per_user
    if actual_aggregate <= OLD_SHARED_BUCKET_PER_HOUR:
        print(
            f"  [!] degraded logins left only {actual_aggregate} aggregate requests "
            f"(<= old {OLD_SHARED_BUCKET_PER_HOUR}/hour bucket) - a pass would be inconclusive"
        )
    print(f"\n=== Phase 2: collapse burst ({len(burst_users)} users) ===")
    burst_results: list = []
    with ThreadPoolExecutor(max_workers=len(burst_users)) as pool:
        futures = [
            pool.submit(
                run_user_burst,
                sessions[email],
                base_url,
                email,
                opts.requests_per_user,
                opts.duration,
                burst_results,
            )
            for email in burst_users
        ]
        for future in futures:
            future.result()
    burst_statuses = summarize("Phase 2 (collapse burst)", burst_results)

    # --- Phase 3: negative control ------------------------------------------
    control_statuses: Counter = Counter()
    if control_email and control_email in sessions:
        print(
            f"\n=== Phase 3: negative control ({control_email}, "
            f"{opts.control_requests} unpaced requests) ==="
        )
        control_results: list = []
        for _ in range(opts.control_requests):
            status, latency = poll_me(sessions[control_email], base_url)
            control_results.append((control_email, status, latency))
        control_statuses = summarize("Phase 3 (negative control)", control_results)

    # --- Verdict --------------------------------------------------------------
    print("\n=== Verdict ===")
    failures = []
    burst_429 = burst_statuses.get(429, 0)
    burst_ok = burst_statuses.get(200, 0)
    if burst_429:
        failures.append(
            f"phase 2 saw {burst_429} x 429 - users are still collapsing into a "
            "shared rate-limit bucket (fix absent or X-Forwarded-For chain broken)"
        )
    else:
        print(f"  [PASS] phase 2: 0x 429 across {len(burst_results)} aggregated requests")
    if burst_ok < len(burst_results) - burst_429:
        non_200 = len(burst_results) - burst_ok - burst_429
        print(f"  [WARN] phase 2: {non_200} non-200/non-429 responses (check summary above)")

    if control_email:
        if control_statuses.get(429, 0):
            print(f"  [PASS] phase 3: limiter active ({control_statuses[429]}x 429 for one user)")
        else:
            failures.append(
                "phase 3 saw no 429 - the per-user limiter never fired; it may be "
                "disabled (RATELIMIT_ENABLED=False?) or the bucket is split across "
                "too many workers (memory:// storage) - raise --control-requests"
            )
    elif control_login_failed:
        failures.append("phase 3 control account failed login - limiter activity NOT verified")
    else:
        print("  [SKIP] phase 3 not run (--skip-control) - limiter activity NOT verified")

    if failures:
        for failure in failures:
            print(f"  [FAIL] {failure}")
        return 1
    print("\nResult: PASS - per-user rate-limit fix holds under IP-collapse conditions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
