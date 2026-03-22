# Profile Management & Email Change

## Overview

The admin profile page (`/pages/admin/profile`) allows authenticated users to manage their personal information, generate API keys, and (for non-SAML users) change their email address.

## Features

### Profile Editing

Users can update the following fields via `PUT /api/1/me/`:

| Field | Backend field | Editable |
|-------|--------------|----------|
| First name | `first_name` | Yes |
| Last name | `last_name` | Yes |
| Biography | `about` | Yes |
| Website | `website` | Yes |
| Profile photo | `avatar` | Yes (upload) |
| Email | `email` | Via confirmation flow |
| API Key | `apikey` | Generated on demand |

### API Key Generation

- **Endpoint**: `POST /api/1/me/apikey`
- Generates a JWT (HS512) containing the user's ID and timestamp
- The key is stored in the user model and returned in the response
- To revoke: `DELETE /api/1/me/apikey`
- API keys are **based on user ID**, not email — they remain valid after email changes

### Avatar Upload

- **Endpoint**: `POST /api/1/me/avatar`
- Accepts `multipart/form-data` with a `file` field
- Max size: 4 MB
- Accepted formats: JPG, JPEG, PNG

## Email Change Flow

### Architecture

The email change uses the Flask-Security blueprint (`/change-email`), not the REST API. The frontend proxies requests through a Next.js route handler to forward cookies and CSRF tokens.

```
[Browser] --POST--> [Next.js /change-email route] --POST--> [Backend /change-email]
                                                                   |
                                                          Sends confirmation email
                                                                   |
[User clicks link] --GET--> [Backend /confirm-change-email/<token>]
                                                                   |
                                                          Updates user.email
```

### Step-by-step

1. User clicks "Alterar e-mail" on the profile page
2. Frontend fetches a CSRF token via `GET /csrf`
3. User enters the new email address
4. Frontend sends `POST /change-email` with `new_email`, `new_email_confirm`, and `csrf_token`
5. Backend generates a signed token containing:
   - User's `fs_uniquifier` (unique session identifier)
   - Hash of the **current** email
   - The **new** email address
6. Backend sends a confirmation email to the **new** address
7. User clicks the confirmation link (`/confirm-change-email/<token>`)
8. Backend validates:
   - Token is not expired
   - User still exists
   - Current email hash matches (email hasn't changed since request)
   - New email is not already taken by another user
9. If valid, updates `user.email` to the new address

### Security Safeguards

| Safeguard | Description |
|-----------|-------------|
| Token expiration | Confirmation link expires (configurable via `CONFIRM_EMAIL_WITHIN`) |
| Old email hash | Token is invalidated if email changes between request and confirmation |
| Password change invalidation | Token contains `fs_uniquifier`, which rotates on password change |
| Uniqueness check | New email is validated against existing users at confirmation time |
| CSRF protection | Request requires a valid CSRF token |

### SAML Users Restriction

Users who authenticated via SAML (Autenticacao.gov.pt) or ProConnect **cannot change their email** through the frontend. This is because:

1. **SSO identity mismatch**: SAML/ProConnect login looks up users by email (`datastore.find_user(email=...)`). If a user changes their email locally, the next SSO login would fail to find their account or create a duplicate.
2. **IdP is the source of truth**: For federated users, the Identity Provider manages the email address. Local changes would create inconsistencies.

The frontend detects SAML users via the `samlLogin` flag from `AuthContext` and hides the "Alterar e-mail" button accordingly.

### Affected System Areas

Changing email affects the following parts of the system:

| Area | Impact | Risk Level |
|------|--------|------------|
| Local login | User must use new email to log in | Low (expected) |
| OAuth2 password grant | Token requests use email as username | Low (expected) |
| Password reset | Reset emails go to new address | Low (expected) |
| Celery tasks (notifications) | Tasks queued with old email may fail lookup | Medium |
| MongoDB text index | Email is indexed with weight 10 for search | Low (auto-updated) |
| API keys | No impact (ID-based, not email-based) | None |
| Frontend session | No impact (ID-based auth context) | None |

## Files

### Frontend

| File | Purpose |
|------|---------|
| `src/components/admin/profile/ProfileClient.tsx` | Profile form with save, API key, email change UI |
| `src/app/change-email/route.ts` | Next.js route handler proxying to backend |
| `src/services/api.ts` | API functions: `fetchFullProfile`, `updateProfile`, `uploadAvatar`, `generateApiKey`, `clearApiKey`, `requestEmailChange` |

### Backend

| File | Purpose |
|------|---------|
| `udata/auth/views.py` | `change_email()` and `confirm_change_email()` handlers |
| `udata/auth/forms.py` | `ChangeEmailForm` validation |
| `udata/auth/mails.py` | Confirmation email template |
| `udata/core/user/models.py` | User model with `email` (unique), `apikey`, `generate_api_key()` |
| `udata/core/user/api.py` | `PUT /me/` profile update, `POST /me/apikey` key generation |
| `udata/core/user/forms.py` | `UserProfileForm` validation |
