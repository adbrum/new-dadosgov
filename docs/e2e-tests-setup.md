# E2E Tests Setup - dados.gov.pt

Guide to set up and run the Playwright E2E test suite for the dados.gov.pt portal.

## Prerequisites

- Node.js 22+ and npm
- Python 3.11+ with `openpyxl` installed
- Backend running on `http://localhost:7000`
- Frontend running on `http://localhost:3000`
- Playwright browsers installed (`npx playwright install chromium`)

## Test Users

Two dedicated test users are configured for E2E testing, both associated with the organization **"Agencia para a Reforma Tecnologica do Estado"**.

| Role | Email | Password | System Admin | Org Role |
|------|-------|----------|--------------|----------|
| Admin | `e2e-admin@dados.gov.pt` | `E2eAdmin2026!` | Yes | admin |
| Editor | `e2e-editor@dados.gov.pt` | `E2eEditor2026!` | No | editor |

### Recreating test users

If the test users need to be recreated (e.g., on a fresh database):

```bash
cd backend

# Create admin user (system administrator)
uv run udata user create \
  --first-name "E2E" --last-name "Admin" \
  --email "e2e-admin@dados.gov.pt" \
  --password "E2eAdmin2026!" --admin

# Create editor user (regular user)
uv run udata user create \
  --first-name "E2E" --last-name "Editor" \
  --email "e2e-editor@dados.gov.pt" \
  --password "E2eEditor2026!"

# Add both users to the organization
uv run python3 -c "
from udata.app import create_app
app = create_app()
with app.app_context():
    from udata.models import User
    from udata.core.organization.models import Organization, Member
    from datetime import datetime

    admin = User.objects(email='e2e-admin@dados.gov.pt').first()
    editor = User.objects(email='e2e-editor@dados.gov.pt').first()
    org = Organization.objects(slug='agencia-para-a-reforma-tecnologica-do-estado').first()

    org.members.append(Member(user=admin, role='admin', since=datetime.utcnow()))
    org.members.append(Member(user=editor, role='editor', since=datetime.utcnow()))
    org.save()
    print('Users added to organization.')
"
```

### Overriding credentials via environment variables

The test credentials can be overridden without modifying code:

```bash
TEST_ADMIN_EMAIL=other-admin@example.com \
TEST_ADMIN_PASSWORD=OtherPass123! \
TEST_EDITOR_EMAIL=other-editor@example.com \
TEST_EDITOR_PASSWORD=OtherPass123! \
npm run test:e2e:backoffice
```

## Test Structure

```
frontend/tests/
├── e2e/
│   ├── frontend-public/          # 19 spec files (181 tests)
│   │   ├── 01-homepage.spec.ts          # HP-01 to HP-13
│   │   ├── 02-search.spec.ts            # PQ-01 to PQ-12
│   │   ├── 03-datasets-listing.spec.ts  # DL-01 to DL-13
│   │   ├── 04-datasets-detail.spec.ts   # DD-01 to DD-17
│   │   ├── 05-organizations-listing.spec.ts  # OL-01 to OL-07
│   │   ├── 06-organizations-detail.spec.ts   # OD-01 to OD-10
│   │   ├── 07-reuses-listing.spec.ts    # RL-01 to RL-09
│   │   ├── 08-reuses-detail.spec.ts     # RD-01 to RD-09
│   │   ├── 09-dataservices.spec.ts      # SD-01 to SD-06
│   │   ├── 10-datastories.spec.ts       # DS-01 to DS-05
│   │   ├── 11-themes.spec.ts            # TM-01 to TM-07
│   │   ├── 12-minicourses.spec.ts       # MC-01 to MC-10
│   │   ├── 13-articles.spec.ts          # NT-01 to NT-06
│   │   ├── 14-authentication.spec.ts    # AU-01 to AU-13
│   │   ├── 15-user-profile.spec.ts      # PF-01 to PF-05
│   │   ├── 16-discussions.spec.ts       # DI-01 to DI-07
│   │   ├── 17-informative-pages.spec.ts # PI-01 to PI-10
│   │   ├── 18-header-footer.spec.ts     # NV-01 to NV-12
│   │   └── 19-responsiveness.spec.ts    # RA-01 to RA-10
│   └── backoffice/               # 14 spec files (144 tests)
│       ├── 01-datasets.spec.ts          # DS-01 to DS-20
│       ├── 02-reuses.spec.ts            # RU-01 to RU-09
│       ├── 03-organizations.spec.ts     # ORG-01 to ORG-12
│       ├── 04-dataservices.spec.ts      # API-01 to API-07
│       ├── 05-harvesters.spec.ts        # HV-01 to HV-06
│       ├── 06-posts.spec.ts             # PO-01 to PO-06
│       ├── 07-topics.spec.ts            # TP-01 to TP-06
│       ├── 08-community-resources.spec.ts  # CR-01 to CR-04
│       ├── 09-editorial.spec.ts         # ED-01 to ED-04
│       ├── 10-permissions.spec.ts       # PM-01 to PM-19
│       ├── 11-integration.spec.ts       # IA-01 to IA-12
│       ├── 12-form-validation.spec.ts   # VL-01 to VL-25
│       ├── 13-user-management.spec.ts   # US-01 to US-06
│       └── 14-navigation-ui.spec.ts     # UI-01 to UI-08
├── helpers/
│   └── auth.ts                   # Login helpers (loginAsAdmin, loginAsEditor)
└── update-excel-results.py       # Script to update Excel test notebooks
```

## Running Tests

### npm scripts

```bash
cd frontend

# Run frontend public tests (no auth needed)
npm run test:e2e

# Run backoffice tests (requires test users)
npm run test:e2e:backoffice

# Run all tests
npm run test:e2e:all

# Open HTML report in browser
npm run test:e2e:report
```

### Running specific tests

```bash
cd frontend

# Run a single spec file
npx playwright test tests/e2e/frontend-public/01-homepage.spec.ts

# Run tests matching a pattern
npx playwright test -g "HP-01"

# Run with visible browser (headed mode)
npx playwright test --headed tests/e2e/frontend-public/01-homepage.spec.ts

# Run with debug inspector
npx playwright test --debug tests/e2e/frontend-public/01-homepage.spec.ts
```

## Updating Excel Test Notebooks

After running the tests, update the Excel test notebooks with results:

```bash
cd frontend

# Run all tests (generates JSON report)
npx playwright test --project=frontend-public --project=backoffice

# Update Excel files (creates timestamped copies, originals untouched)
python3 tests/update-excel-results.py

# Preview without saving
python3 tests/update-excel-results.py --dry-run
```

The script:
1. Reads `test-results/e2e-results.json`
2. Creates a timestamped copy of each Excel file (e.g., `caderno_testes_frontend_publico_20260322_153045.xlsx`)
3. Fills the copy with OK/NOK results, test date, and observations
4. Updates the summary table with OK counts per section
5. Leaves the original files untouched

### Excel column mapping

| Column | Field | Values |
|--------|-------|--------|
| F | OK/NOK | `OK` (passed), `NOK` (failed), empty (skipped) |
| G | Data do Teste | `dd/mm/yyyy` |
| H | Observacoes | `Teste automatizado - Playwright` / error message / `Teste ignorado (skip)` |

## Test ID Reference

Each test has a unique ID matching the test notebooks:

| Prefix | Section | Notebook |
|--------|---------|----------|
| HP | Homepage | Frontend |
| PQ | Global Search | Frontend |
| DL | Datasets Listing | Frontend |
| DD | Datasets Detail | Frontend |
| OL | Organizations Listing | Frontend |
| OD | Organizations Detail | Frontend |
| RL | Reuses Listing | Frontend |
| RD | Reuses Detail | Frontend |
| SD | Data Services | Frontend |
| DS | Data Stories (Frontend) / Datasets (Backoffice) | Both |
| TM | Themes | Frontend |
| MC | Mini-courses | Frontend |
| NT | Articles/News | Frontend |
| AU | Authentication | Frontend |
| PF | User Profile | Frontend |
| DI | Discussions | Frontend |
| PI | Informative Pages | Frontend |
| NV | Header/Footer Navigation | Frontend |
| RA | Responsiveness/Accessibility | Frontend |
| RU | Reuses CRUD | Backoffice |
| ORG | Organizations CRUD | Backoffice |
| API | Data Services CRUD | Backoffice |
| HV | Harvesters | Backoffice |
| PO | Posts | Backoffice |
| TP | Topics | Backoffice |
| CR | Community Resources | Backoffice |
| ED | Editorial | Backoffice |
| PM | Permissions | Backoffice |
| IA | Integration (Backoffice to Portal) | Backoffice |
| VL | Form Validation | Backoffice |
| US | User Management | Backoffice |
| UI | Navigation/UI | Backoffice |
