# SAML Account Linking — CMD/eIDAS Duplicate Prevention

> **Updated 2026-08-18 (udata-pt#94):** the automatic merge described in earlier
> versions of this document was removed. A CMD identity is now linked to an
> existing account **only after the user proves ownership** through the
> migration wizard. See "Solution — Ownership-Confirmed Linking" below; the
> CLI commands remain valid for cleaning up duplicates created before #94.

## Problem

When a user with a traditional account (email/password) logs in for the first time via CMD (Autenticação.gov SAML), the system may create a **duplicate account** instead of linking the CMD identity to the existing one.

This happens because:

1. The CMD IdP provides email, NIC, first_name, last_name.
2. The IdP email may differ from the traditional account email (or be absent).
3. The NIC does not exist yet in the database (first CMD login).
4. With no email or NIC match, a new user is created with a placeholder email (`saml-{NIC}@autenticacao.gov.pt`).

**Result:** Two accounts for the same person — the traditional one (with roles, datasets, organizations) and a new empty SAML one.

### NIC Storage — HMAC-SHA256 Hashing

The NIC (Numero de Identificacao Civil) is personal data and **must not be stored in plain text**. All NIC values are hashed using HMAC-SHA256 with the Flask `SECRET_KEY` before being stored in `extras.auth_nic`.

- **Function:** `_hash_nic(nic)` in `saml_govpt.py` and `commands.py`
- **Algorithm:** HMAC-SHA256 (deterministic — same NIC always produces same hash, enabling DB lookups)
- **Key:** Flask `SECRET_KEY` (server-specific, not reversible without it)
- **Format:** 64-character lowercase hex string

**Migration command:** To hash existing plain-text NICs in the database:
```bash
udata user hash-nics --dry-run   # preview
udata user hash-nics             # execute
```

---

## Solution — Ownership-Confirmed Linking

**File:** `backend/udata/auth/saml/saml_plugin/saml_govpt.py`

### Resolution Order (`_find_or_create_saml_user`)

| Step | Match by     | Outcome                                                       |
|------|-------------|----------------------------------------------------------------|
| 1    | NIC (hashed, `extras.auth_nic`) | Direct login — the **only** path that logs in without confirmation |
| 2    | Email (account without a linked NIC) | `migration_candidate` → migration wizard, never auto-linked |
| 3    | `first_name` + `last_name` (case-insensitive, accounts without NIC) | `migration_candidate`; with homonyms the candidate is `None` and the wizard asks the user to identify the account | 
| 4    | No match    | New account is created; the redirect carries `cmd_new_account=1` |

### Linking via the Migration Wizard

A `migration_candidate` is redirected to the frontend wizard (`/migrate-account`,
`?no_email=true` when the IdP provided no email), backed by the
`/saml/migration/*` endpoints (`check`, `pending`, `search`, `send-code`,
`confirm`, `skip`). Ownership is proven by one of:

- **Email code** — a 6-digit code sent to the account's address, bound to the
  account it was issued for (re-pointing the candidate invalidates it),
  5 attempts, expiring;
- **Full login** — email + password of the account, 5 attempts per session,
  generic errors to avoid account enumeration.

On success the hashed NIC is stored on the account and the **password is
kept** — both login methods remain valid. Roles, organizations and owned
content are untouched. Accounts already linked to another CMD identity are
never candidates.

### `MIGRATION_MODE_ENABLED` (kill-switch)

Defined in `udata.cfg` (`_env_bool("MIGRATION_MODE_ENABLED", True)`), default
**True**. It gates the wizard redirect and all `/saml/migration/*` endpoints
(403 when off). When disabled, a matched account is **never** logged into
without proof — a new account is created instead (users then accumulate
duplicates until it is re-enabled).

### Historical: auto-merge (removed in udata-pt#94)

Until #94 the backend auto-merged the NIC into an account matched by email or
by a unique first+last name, with no ownership proof, and cleared the password
on merge. This allowed a CMD user to be logged into a homonym's account and
was removed for security. The CLI commands below remain the tool for cleaning
up duplicate accounts created during that period.

---

## CLI Commands

### `udata user fix-cmd-duplicates` — Automatic Bulk Merge

Automatically finds and merges duplicate SAML accounts (emails starting with `saml-*`).

**File:** `backend/udata/core/user/commands.py`

```bash
# Preview what would be done (no changes made)
udata user fix-cmd-duplicates --dry-run

# Execute the merge
udata user fix-cmd-duplicates
```

#### What it does

1. Finds all users with placeholder SAML emails (`saml-*`).
2. For each duplicate, looks up the traditional account by `first_name` + `last_name` (case-insensitive exact match).
3. **Skips** if:
   - The duplicate has no NIC (`auth_nic`) to merge.
   - No traditional account is found with the same name.
   - Multiple traditional accounts match (ambiguous — use `merge-saml` instead).
   - The traditional account already has the same numeric NIC (already merged).
4. Hashes `extras.auth_nic` (HMAC-SHA256) and stores in the traditional account.
5. Hard-deletes the duplicate SAML account from the database.

#### Example output

```
Found 3 duplicate SAML account(s)
MERGED NIC 32134714 into user@example.com | deleted saml-32134714@autenticacao.gov.pt
OVERWRITTEN+MERGED NIC 32135653 into admin@example.com | deleted saml-32135653@autenticacao.gov.pt
SKIP saml-99999999@autenticacao.gov.pt (Maria Silva) — multiple matches: ['maria1@example.com', 'maria2@example.com']
✔ Merged 2 account(s), skipped 1
```

---

### `udata user merge-saml` — Manual Merge (Ambiguous Cases)

For cases where `fix-cmd-duplicates` cannot auto-resolve (e.g. multiple users with the same name), use this command to specify the exact target account.

```bash
# Preview
udata user merge-saml saml-32135653@autenticacao.gov.pt joao.soares@ama.gov.pt --dry-run

# Execute
udata user merge-saml saml-32135653@autenticacao.gov.pt joao.soares@ama.gov.pt
```

#### What it does

1. Takes the SAML duplicate email and the target traditional email as arguments.
2. Copies `extras.auth_nic` from the duplicate into the target account.
3. Hard-deletes the duplicate SAML account.
4. The target account retains all its roles, datasets, and organizations.

---

## Troubleshooting

### User logs in via CMD but has no admin permissions

**Cause:** A duplicate account was created (without admin role) and the user is logged into that account instead of their original admin account.

**Diagnosis:**
```bash
# Check for duplicate SAML accounts
udata user fix-cmd-duplicates --dry-run
```

**Fix:**
1. If `fix-cmd-duplicates` can auto-resolve: run without `--dry-run`.
2. If multiple name matches: use `merge-saml` with the correct target email.
3. The user must log out and log in again via CMD to use the correct account.

### NIC match not working after merge

**Cause (fixed):** The NIC query used `datastore.find_user(extras={"auth_nic": ...})` which matched the entire `extras` dict exactly. If `extras` had any other keys, the query returned nothing.

**Fix (2026-03-27):** Changed to `User.objects(extras__auth_nic=user_nic).first()` which queries only the nested `auth_nic` key.

### Encrypted/plain vs hashed NIC mismatch

**Cause (fixed):** Legacy accounts stored `auth_nic` as encrypted or plain values. When a user was found by email/name and already had an NIC, the code returned early without updating, so the NIC format stayed inconsistent and future NIC matches failed.

**Fix (2026-03-27):** All NIC values are now hashed with HMAC-SHA256 before storage. The auto-merge compares the stored hash with the hash of the incoming NIC. If they differ, it re-hashes. Run `udata user hash-nics` to migrate existing plain-text values.

---

## Related Files

| File | Purpose |
|------|---------|
| `backend/udata/auth/saml/saml_plugin/saml_govpt.py` | SAML authentication handler (resolution order, migration wizard endpoints) |
| `backend/udata/core/user/commands.py` | CLI commands `fix-cmd-duplicates`, `merge-saml` and `hash-nics` |
| `backend/udata/core/user/models.py` | User model (`extras.auth_nic` field) |
| `backend/udata.cfg` | `MIGRATION_MODE_ENABLED` flag (default `True`) |
| `frontend/src/components/login/MigrateAccountClient.tsx` | Migration wizard UI |
| `backend/udata/tests/frontend/test_saml.py` | Wizard + security regression tests |
| `docs/migration-plan-of-legacy-accounts-to-CMD-ticket-40.md` | Full migration plan (TICKET-40) |
