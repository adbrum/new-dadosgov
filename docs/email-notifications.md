# Email Notifications

This document describes all email notifications sent by the backend, organized by category. Each entry includes the trigger action, recipients, subject, and the source files involved.

## Table of Contents

- [1. Authentication](#1-authentication)
- [2. Account Management](#2-account-management)
- [3. Organization Membership](#3-organization-membership)
- [4. Organization Badges](#4-organization-badges)
- [5. Reuses](#5-reuses)
- [6. Discussions](#6-discussions)
- [7. Legal Notices](#7-legal-notices)
- [8. SAML Account Migration](#8-saml-account-migration)
- [9. Harvest Warnings](#9-harvest-warnings)
- [Summary](#summary)
- [Architecture](#architecture)
- [Testing](#testing)

---

## 1. Authentication

Managed by Flask-Security. Templates are rendered via custom `MailMessage` builders in `udata/auth/mails.py`, integrated through `render_security_template()` in `udata/auth/__init__.py`.

### 1.1 Welcome (Account Creation)

| Field | Value |
|-------|-------|
| **Subject** | "Confirm your email address" |
| **Trigger** | User registers a new account (`POST /register/`) |
| **Recipients** | The new user |
| **Content** | Welcome message, CTA to confirm email address |
| **Builder** | `udata/auth/mails.py` &rarr; `welcome(confirmation_link)` |

### 1.2 Welcome Existing (Duplicate Registration)

| Field | Value |
|-------|-------|
| **Subject** | "Account information" |
| **Trigger** | Registration attempted with an email that already exists |
| **Recipients** | The existing user |
| **Content** | Informs that a registration was attempted, offers password reset link |
| **Builder** | `udata/auth/mails.py` &rarr; `welcome_existing(recovery_link)` |

### 1.3 Confirmation Instructions

| Field | Value |
|-------|-------|
| **Subject** | "Confirm your email address" |
| **Trigger** | User requests re-send of confirmation email (`GET /confirm/`) |
| **Recipients** | The unconfirmed user |
| **Content** | CTA to confirm email address |
| **Builder** | `udata/auth/mails.py` &rarr; `confirmation_instructions(confirmation_link)` |

### 1.4 Password Reset Instructions

| Field | Value |
|-------|-------|
| **Subject** | "Reset your password" |
| **Trigger** | User requests password reset (`POST /reset/`) |
| **Recipients** | The user |
| **Content** | Informs about reset request, CTA with reset link containing token |
| **Builder** | `udata/auth/mails.py` &rarr; `reset_instructions(reset_token)` |

### 1.5 Password Reset Notice

| Field | Value |
|-------|-------|
| **Subject** | "Your password has been reset" |
| **Trigger** | User successfully resets password via token (`POST /reset/<token>`) |
| **Recipients** | The user |
| **Content** | Confirmation that password was reset |
| **Builder** | `udata/auth/mails.py` &rarr; `reset_notice()` |

### 1.6 Password Change Notice

| Field | Value |
|-------|-------|
| **Subject** | "Your password has been changed" |
| **Trigger** | User changes password while logged in (`POST /change/`) |
| **Recipients** | The user |
| **Content** | Confirmation that password was changed, CTA to reset if it wasn't them |
| **Builder** | `udata/auth/mails.py` &rarr; `change_notice()` |

---

## 2. Account Management

### 2.1 Change Email Confirmation

| Field | Value |
|-------|-------|
| **Subject** | "Confirm your email address" |
| **Trigger** | User requests email change (`POST /change-email`) |
| **Recipients** | The **new** email address |
| **Content** | CTA to confirm the new email address |
| **Source** | `udata/auth/views.py` &rarr; `send_change_email_confirmation_instructions()` |

### 2.2 Account Deletion

| Field | Value |
|-------|-------|
| **Subject** | "Account deletion" |
| **Trigger** | User account is deleted (`User.mark_as_deleted(notify=True)`) |
| **Recipients** | The deleted user |
| **Content** | Confirmation that account has been deleted |
| **Source** | `udata/core/user/mails.py` &rarr; `account_deletion()` |
| **Sender** | `udata/core/user/models.py` &rarr; `User.mark_as_deleted()` |

### 2.3 Inactive User Warning

| Field | Value |
|-------|-------|
| **Subject** | "Inactivity of your {site} account" |
| **Trigger** | Scheduled job detects user inactivity exceeding threshold |
| **Recipients** | The inactive user |
| **Content** | Inactivity warning, CTA to log in, deletion countdown |
| **Config** | `YEARS_OF_INACTIVITY_BEFORE_DELETION`, `DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY` |
| **Source** | `udata/core/user/mails.py` &rarr; `inactive_user(user)` |
| **Sender** | `udata/core/user/tasks.py` &rarr; `notify_inactive_users()` (scheduled job) |

### 2.4 Inactive Account Deleted

| Field | Value |
|-------|-------|
| **Subject** | "Deletion of your inactive {site} account" |
| **Trigger** | Scheduled job deletes user after inactivity period + notification delay |
| **Recipients** | The deleted user |
| **Content** | Confirmation that account was deleted due to inactivity |
| **Source** | `udata/core/user/mails.py` &rarr; `inactive_account_deleted()` |
| **Sender** | `udata/core/user/tasks.py` &rarr; `delete_inactive_users()` (scheduled job) |

---

## 3. Organization Membership

All triggered via Celery tasks in `udata/core/organization/tasks.py`. Mail builders in `udata/core/organization/mails.py`.

### 3.1 Membership Request

| Field | Value |
|-------|-------|
| **Subject** | "New membership request" |
| **Trigger** | User requests to join an organization |
| **Recipients** | All organization **admin** members |
| **Content** | Request reason/comment, link to admin panel |
| **Task** | `notify_membership_request(org_id, request_id)` |

### 3.2 Membership Accepted

| Field | Value |
|-------|-------|
| **Subject** | "Your invitation to join an organization has been accepted" |
| **Trigger** | Admin accepts a membership request |
| **Recipients** | The requesting user |
| **Content** | Approval notice, link to organization |
| **Task** | `notify_membership_response(org_id, request_id)` (when status is `"accepted"`) |

### 3.3 Membership Refused

| Field | Value |
|-------|-------|
| **Subject** | "Membership refused" |
| **Trigger** | Admin refuses a membership request |
| **Recipients** | The requesting user |
| **Content** | Rejection notice |
| **Task** | `notify_membership_response(org_id, request_id)` (when status is not `"accepted"`) |

### 3.4 New Member Added

| Field | Value |
|-------|-------|
| **Subject** | "You have been added as a member of an organization" |
| **Trigger** | Admin directly adds a user to the organization |
| **Recipients** | The new member |
| **Content** | Welcome notice, link to organization |
| **Task** | `notify_new_member(org_id, email)` |

---

## 4. Organization Badges

Triggered when an admin assigns a badge to an organization. All use the `@notify_new_badge` decorator in `udata/core/organization/tasks.py`. Mail builders in `udata/core/organization/mails.py`.

| Badge | Subject | Task |
|-------|---------|------|
| Certified | "Your organization has been certified" | `notify_badge_certified` |
| Public Service | "Your organization has been identified as a public service" | `notify_badge_public_service` |
| Local Authority | "Your organization has been identified as a local authority" | `notify_badge_local_authority` |
| Company | "Your organization has been identified as a company" | `notify_badge_company` |
| Association | "Your organization has been identified as an association" | `notify_badge_association` |

**Recipients:** All organization members.

---

## 5. Reuses

### 5.1 New Reuse on Dataset

| Field | Value |
|-------|-------|
| **Subject** | "New reuse on your dataset" |
| **Trigger** | A reuse referencing a dataset is created via API (`POST /api/1/reuses/`) |
| **Recipients** | Organization members (if dataset belongs to org) **or** dataset owner |
| **Content** | Reuse title, CTA to view the reuse |
| **Source** | `udata/core/reuse/mails.py` &rarr; `new_reuse(reuse, dataset)` |
| **Task** | `udata/core/reuse/tasks.py` &rarr; `notify_new_reuse(reuse_id)` |

---

## 6. Discussions

Triggered via signal handlers in `udata/core/discussions/tasks.py`. Mail builders in `udata/core/discussions/mails.py`.

### 6.1 New Discussion

| Field | Value |
|-------|-------|
| **Subject** | "A new discussion has been opened on your {type}" |
| **Trigger** | User opens a new discussion on a dataset, reuse, or organization |
| **Recipients** | Resource owner (organization members or individual owner) |
| **Content** | Discussion title, initial comment, CTA to reply |
| **Task** | `notify_new_discussion(discussion_id)` |

### 6.2 New Discussion Comment

| Field | Value |
|-------|-------|
| **Subject** | "A new comment has been added to a discussion" |
| **Trigger** | User adds a comment to an existing discussion |
| **Recipients** | Resource owner + all previous comment authors (excluding the commenter) |
| **Content** | Comment text, CTA to reply |
| **Task** | `notify_new_discussion_comment(discussion_id, message)` |

### 6.3 Discussion Closed

| Field | Value |
|-------|-------|
| **Subject** | "A discussion has been closed" |
| **Trigger** | Owner or admin closes a discussion |
| **Recipients** | Resource owner + all comment authors (excluding the closer) |
| **Content** | Closure notice, optional closing comment, CTA to view |
| **Task** | `notify_discussion_closed(discussion_id, message)` |

---

## 7. Legal Notices

### 7.1 Content Deletion Legal Notice

| Field | Value |
|-------|-------|
| **Subject** | "Deletion of your {content_type}" |
| **Trigger** | Sysadmin deletes content with `send_legal_notice=true` parameter via API |
| **Recipients** | Content owner or organization admin members |
| **Content** | Formal legal notice with terms of use reference and administrative appeal information |
| **Config** | `TELERECOURS_URL` (administrative appeal URL) |
| **Source** | `udata/core/legal/mails.py` &rarr; `send_legal_notice_on_deletion(obj, args)` |
| **Eligible objects** | Dataset, Reuse, Dataservice, Organization, User, Discussion, Message |

---

## 8. SAML Account Migration

### 8.1 Migration Verification Code

| Field | Value |
|-------|-------|
| **Subject** | "Account migration verification code" |
| **Trigger** | User attempts to migrate a legacy password account to SAML/CMD authentication |
| **Recipients** | The user's email |
| **Content** | Verification code for linking CMD identity, 10-minute expiry notice |
| **Source** | `udata/auth/saml/saml_plugin/saml_govpt.py` &rarr; `_send_migration_code(user, code)` |

---

## 9. Harvest Warnings

### 9.1 Missing Datasets Warning

| Field | Value |
|-------|-------|
| **Subject** | "Relatório harvesting dados.gov - {source}" |
| **Trigger** | Harvest job completes and discovers datasets that disappeared from source |
| **Recipients** | Organization admin members (To), all platform admins (BCC), dados@ama.pt (CC) |
| **Content** | List of datasets now marked as private due to absence from harvest source |
| **Source** | `udata/harvest/backends/tools/harvester_utils.py` &rarr; `missing_datasets_warning()` |

> **Note:** This email uses legacy Flask-Mail directly, not the `MailMessage` system.

---

## Summary

| Category | Count | Delivery Mechanism |
|----------|------:|--------------------|
| Authentication | 6 | Flask-Security + custom `MailMessage` rendering |
| Account Management | 4 | Direct `send_mail()` / Celery tasks |
| Organization Membership | 4 | Celery tasks |
| Organization Badges | 5 | Celery tasks |
| Reuses | 1 | Celery task |
| Discussions | 3 | Signal handlers + Celery tasks |
| Legal Notices | 1 | API endpoint |
| SAML Migration | 1 | Direct `send_mail()` |
| Harvest Warnings | 1 | Legacy Flask-Mail |
| **Total** | **26** | |

---

## Architecture

### Mail Sending Flow

```
Action (API / Task / Signal)
  │
  ├─ Authentication emails ──► Flask-Security MailUtil
  │                                │
  │                                ├─ Production: Flask-Mail (SMTP)
  │                                └─ Debug/Test: NoopMailUtil (log only)
  │
  └─ All other emails ──► udata.mail.send_mail()
                               │
                               ├─ Production (SEND_MAIL=True): Flask-Mail (SMTP)
                               └─ Debug/Test (SEND_MAIL=False): log + emit mail_sent signal
```

### Key Files

| File | Purpose |
|------|---------|
| `udata/mail.py` | `MailMessage` class, `send_mail()`, `mail_sent` signal |
| `udata/auth/mails.py` | Authentication email builders (Flask-Security integration) |
| `udata/auth/__init__.py` | `render_security_template()`, `NoopMailUtil` |
| `udata/auth/views.py` | Auth views that trigger email sending |
| `udata/core/user/mails.py` | Account deletion / inactivity emails |
| `udata/core/organization/mails.py` | Membership + badge emails |
| `udata/core/reuse/mails.py` | New reuse notification |
| `udata/core/discussions/mails.py` | Discussion notification emails |
| `udata/core/legal/mails.py` | Legal deletion notices |
| `udata/settings.py` | Flask-Security configuration (`SECURITY_*` settings) |

### Configuration

Relevant settings in `udata/settings.py`:

| Setting | Description |
|---------|-------------|
| `SEND_MAIL` | Enable/disable mail sending (defaults to `not DEBUG`) |
| `MAIL_DEFAULT_SENDER` | Default sender address |
| `SECURITY_CONFIRMABLE` | Require email confirmation on registration |
| `SECURITY_RECOVERABLE` | Enable password reset |
| `SECURITY_CHANGEABLE` | Enable password change |
| `SECURITY_EMAIL_SUBJECT_REGISTER` | Subject for welcome email |
| `SECURITY_EMAIL_SUBJECT_CONFIRM` | Subject for confirmation email |
| `SECURITY_EMAIL_SUBJECT_PASSWORD_RESET` | Subject for password reset email |
| `SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE` | Subject for reset notice email |
| `SECURITY_EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE` | Subject for change notice email |

---

## Testing

### Test Files

| File | Scope |
|------|-------|
| `udata/tests/test_auth_mails.py` | Auth email rendering (txt + html) and `MailMessage` builder validation |
| `udata/tests/api/test_security_api.py` | Auth endpoint integration (register, reset, change password, change email) |
| `udata/tests/reuse/test_reuse_mails.py` | Reuse notification emails (send + content) |
| `udata/tests/organization/test_organization_mails.py` | Organization membership emails (send + content) |

### Testing Approach

- **Authentication emails** (Flask-Security): Cannot be captured with `capture_mails()` because they go through `NoopMailUtil` in test mode. Tests verify template rendering and endpoint responses.
- **All other emails** (`send_mail()`): Can be captured with `capture_mails()` context manager, which hooks into the `mail_sent` blinker signal emitted in debug mode.

```python
from udata.tests.helpers import capture_mails

with capture_mails() as mails:
    # trigger the action that sends email
    notify_new_reuse(str(reuse.id))

assert len(mails) == 1
assert mails[0].recipients[0] == expected_email
assert "expected text" in mails[0].body
```
