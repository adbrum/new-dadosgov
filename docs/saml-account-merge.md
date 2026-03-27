# SAML Account Auto-Merge — CMD/eIDAS Duplicate Prevention

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

## Solution — Auto-Merge

**File:** `backend/udata/auth/saml/saml_plugin/saml_govpt.py`

### Lookup Order (`_find_or_create_saml_user`)

| Step | Match by     | Description                                                  |
|------|-------------|--------------------------------------------------------------|
| 1    | Email       | Exact match against the email provided by the IdP            |
| 2    | NIC         | Match via `extras.auth_nic` (previous CMD login already linked) |
| 3    | Name        | Fallback: `first_name` + `last_name` (case-insensitive)     |
| 4    | No match    | Create new user with placeholder email                       |

### Auto-Merge Logic

When a legacy account is found (any step):

1. If `extras.auth_nic` matches the hashed incoming NIC — normal login, no changes needed.
2. If `extras.auth_nic` is missing or different (e.g. old encrypted/plain value) — the NIC is re-hashed (HMAC-SHA256) and stored.
3. The user is logged in with their existing account (preserving roles, datasets, orgs).
4. Future CMD logins resolve instantly via Step 2 (hashed NIC match).

### Name Matching Safety

Step 3 (name match) only triggers when there is **exactly one** user with that first_name + last_name combination. If multiple users share the same name, no match is made and a new account is created (preventing incorrect merges). These cases require **manual resolution** via `udata user merge-saml`.

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
| `backend/udata/auth/saml/saml_plugin/saml_govpt.py` | SAML authentication handler (auto-merge logic) |
| `backend/udata/core/user/commands.py` | CLI commands `fix-cmd-duplicates` and `merge-saml` |
| `backend/udata/core/user/models.py` | User model (`extras.auth_nic` field) |
| `backend/udata/settings.py` | `MIGRATION_MODE_ENABLED` flag |
| `docs/migration-plan-of-legacy-accounts-to-CMD-ticket-40.md` | Full migration plan (TICKET-40) |
