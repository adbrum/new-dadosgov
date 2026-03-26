# SAML Account Auto-Merge — CMD/eIDAS Duplicate Prevention

## Problem

When a user with a traditional account (email/password) logs in for the first time via CMD (Autenticação.gov SAML), the system may create a **duplicate account** instead of linking the CMD identity to the existing one.

This happens because:

1. The CMD IdP provides email, NIC, first_name, last_name.
2. The IdP email may differ from the traditional account email (or be absent).
3. The NIC does not exist yet in the database (first CMD login).
4. With no email or NIC match, a new user is created with a placeholder email (`saml-{NIC}@autenticacao.gov.pt`).

**Result:** Two accounts for the same person — the traditional one (with roles, datasets, organizations) and a new empty SAML one.

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

When a legacy account is found (any step) and it has **no `auth_nic`**:

1. The NIC from the SAML response is written to `user.extras.auth_nic`.
2. The user is logged in with their existing account (preserving roles, datasets, orgs).
3. Future CMD logins resolve instantly via Step 2 (NIC match).

### Name Matching Safety

Step 3 (name match) only triggers when there is **exactly one** user with that first_name + last_name combination. If multiple users share the same name, no match is made and a new account is created (preventing incorrect merges).

---

## Manual Procedure — Fixing Existing Duplicates

If duplicate accounts already exist in the database, use the following procedure to merge them manually.

### Prerequisites

- Access to MongoDB (via `mongosh`, `mongo`, or `pymongo`)
- MongoDB connection: `mongodb://{SERVER_MONGO}:27017/udata`

### Step 1 — Identify duplicates

Find users with placeholder SAML emails:

```javascript
// mongosh
db.user.find(
  { email: /^saml-/ },
  { _id: 1, first_name: 1, last_name: 1, email: 1, extras: 1 }
)
```

Or with pymongo:

```python
from pymongo import MongoClient

client = MongoClient("mongodb://SERVER_MONGO:27017/udata")
db = client["udata"]

duplicates = db.user.find(
    {"email": {"$regex": "^saml-"}},
    {"_id": 1, "first_name": 1, "last_name": 1, "email": 1, "extras": 1}
)
for u in duplicates:
    nic = u.get("extras", {}).get("auth_nic", "N/A")
    print(f"{u['_id']} | {u.get('first_name')} {u.get('last_name')} | {u['email']} | NIC: {nic}")
```

### Step 2 — Find the traditional account

For each duplicate, find the original account by name or known email:

```javascript
db.user.find(
  { first_name: "João", last_name: "Silva", email: { $not: /^saml-/ } },
  { _id: 1, email: 1, roles: 1, extras: 1 }
)
```

### Step 3 — Merge NIC into the traditional account

```javascript
db.user.updateOne(
  { _id: ObjectId("TRADITIONAL_ACCOUNT_ID") },
  { $set: { "extras.auth_nic": "NIC_VALUE" } }
)
```

### Step 4 — Delete the duplicate SAML account

```javascript
db.user.deleteOne({ _id: ObjectId("DUPLICATE_SAML_ACCOUNT_ID") })
```

### Step 5 — Verify

```javascript
db.user.findOne(
  { _id: ObjectId("TRADITIONAL_ACCOUNT_ID") },
  { email: 1, extras: 1, roles: 1 }
)
// Should show: extras.auth_nic = "NIC_VALUE", roles intact
```

---

## Full Pymongo Script — Bulk Merge

Script to find and merge all existing duplicates in one run:

```python
from pymongo import MongoClient

client = MongoClient("mongodb://SERVER_MONGO:27017/udata")
db = client["udata"]

duplicates = list(db.user.find({"email": {"$regex": "^saml-"}}))
print(f"Found {len(duplicates)} duplicate SAML account(s)\n")

for dup in duplicates:
    nic = dup.get("extras", {}).get("auth_nic")
    fname = dup.get("first_name", "")
    lname = dup.get("last_name", "")

    if not nic:
        print(f"SKIP {dup['_id']} — no NIC to merge")
        continue

    # Find traditional account by name
    candidates = list(db.user.find({
        "first_name": {"$regex": f"^{fname}$", "$options": "i"},
        "last_name": {"$regex": f"^{lname}$", "$options": "i"},
        "email": {"$not": {"$regex": "^saml-"}},
    }))

    if len(candidates) == 0:
        print(f"SKIP {dup['email']} ({fname} {lname}) — no traditional account found")
        continue
    if len(candidates) > 1:
        emails = [c["email"] for c in candidates]
        print(f"SKIP {dup['email']} ({fname} {lname}) — multiple matches: {emails}")
        continue

    target = candidates[0]
    existing_nic = target.get("extras", {}).get("auth_nic")
    if existing_nic:
        print(f"SKIP {target['email']} — already has NIC {existing_nic}")
        continue

    # Merge
    db.user.update_one(
        {"_id": target["_id"]},
        {"$set": {"extras.auth_nic": nic}}
    )
    db.user.delete_one({"_id": dup["_id"]})
    print(f"MERGED NIC {nic} into {target['email']} | deleted {dup['email']}")

print("\nDone.")
```

---

## Related Files

| File | Purpose |
|------|---------|
| `backend/udata/auth/saml/saml_plugin/saml_govpt.py` | SAML authentication handler (auto-merge logic) |
| `backend/udata/core/user/models.py` | User model (`extras.auth_nic` field) |
| `backend/udata/settings.py` | `MIGRATION_MODE_ENABLED` flag |
| `docs/migration-plan-of-legacy-accounts-to-CMD-ticket-40.md` | Full migration plan (TICKET-40) |

## History

| Date       | Action |
|------------|--------|
| 2026-03-26 | Auto-merge logic added to `_find_or_create_saml_user` (name-based fallback) |
| 2026-03-26 | Manual merge: Adriano Leal (`adbrum@outlook.com` ← NIC `32134714`) |
| 2026-03-26 | Manual merge: António Soares (`antonio.soares@ama.gov.pt` ← NIC `32135653`) |
