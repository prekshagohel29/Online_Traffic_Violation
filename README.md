# Online Traffic Violation — Member 3

**Government oversight, administration, analytics, audit and reporting** for the
three-member AI-assisted traffic review and e-Memo college project.

Target repository: https://github.com/prekshagohel29/Online_Traffic_Violation

## Repository scope

This submission contains Member 3's frontend pages, extracted reporting/admin
backend modules, shared database definitions/migrations, focused tests and report
material. Member 1's citizen/authentication screens and Member 2's RTO/video worker
are kept in their separate local packages for their own integration work.

This is a **module submission**. A complete application runs after the shared
application shell/authentication and the other members' modules are merged. This
repository does not pretend that three standalone pages are a complete deployment.
The integration helper connects this module to the exact working college baseline
without duplicating routes or changing the citizen/RTO behavior.

## Features delivered by Member 3

### Government analytics and oversight

- Saved confirmed/pending case counts and sandbox memo totals.
- Case trends grouped by Indian Standard Time dates.
- Source selection: all records, demonstration examples or recorded cases.
- Recorded location and violation-type dropdowns, date-range validation and reset.
- Charts for time, violation type and location, plus memo-status breakdowns.
- Anonymized case summaries: plate/owner details, evidence, raw OCR and reviewer
  information remain restricted to authorized operational roles.
- Shared overview/filter/case-read APIs retain citizen ownership scoping.

### Administration

- Trusted role assignment for USER, RTO, GOVT and ADMIN accounts.
- Existing sessions are revoked when a user's role is changed.
- An administrator cannot change their own role through this screen.
- Project fine policy with server validation and a new version for every update.
- Audit history for important changes.
- Readable video-service, worker, queue and session status.
- Existing trusted device-credential administration retained in the backend.
- Local account provisioning/recovery and database-maintenance CLI support.

### Reports and documentation

- College report with purpose, modules, architecture, database relationships and viva points.
- Demonstration walkthrough and college completion checklist.
- Member-specific API/security tests and integration verification.
- Original-project, model and dataset attribution preserved.

## Three-member ownership map

| Member | Assigned area | Submission status |
|---|---|---|
| 1 | Citizen registration/login/profile, ownership requests, own memos, sandbox receipts and disputes | Kept in `Member_1` for its member's changes/merge |
| 2 | RTO review, evidence, camera/video pipeline, memo issue and dispute decisions | Kept in `Member_2` for its member's changes/merge |
| **3** | **Government/Admin, reporting, audit, database documentation** | **This package** |

This map records responsibility. Commit and report credit should describe actual
development, review, testing and documentation performed by each member. Existing
upstream history/credits are not reassigned by this package.

## File layout

```text
frontend/src/pages/
  GovernmentAnalytics.js       # Charts, filters and oversight
  Admin.js                     # Roles, service status, policy and audit
  ProjectGuide.js              # Shared explanation/demo guidance
backend/
  member3_admin.py              # Admin + government legacy-report endpoints
  member3_reporting.py          # Scoped case reads, filters, overview and redaction
  models.py                    # Shared versioned schema, unchanged
  db.py                        # Shared transactions/connection setup, unchanged
  manage.py                    # Trusted management/migration commands, unchanged
migrations/                    # Versioned schema/private-access/storage upgrades
integration/
  apply_member3.py              # Checked/idempotent shared-core integration
  member3_backend.patch         # Reviewable diff for the two shared files
  member3_baseline.json         # Before/after hashes and baseline identity
tests/
  conftest.py                   # Shared isolated-app/account fixtures
  test_member3.py               # Member-specific behavior/security tests
docs/
  BACKEND_INTEGRATION.md
  TEAM_OWNERSHIP.md
  VALIDATION.md
  COLLEGE_PROJECT_REPORT.md
  COLLEGE_COMPLETION_CHECKLIST.md
  DEMO_GUIDE.md
  BASELINE_TEST_REPORT.md
THIRD_PARTY_NOTICES.md
```

## Integration with Members 1 and 2

1. Merge the shared working baseline from the member packages into the central
   repository. Retain its React app shell, authentication/context, shared UI/styles,
   API utility, Flask core, storage, worker, requirements and launch scripts.
2. Keep the Member 3 files at the paths shown above.
3. From the complete repository root, run:

   ```powershell
   python integration/apply_member3.py
   ```

   The helper verifies the two shared files against the known baseline before
   writing, saves backups under `data/member3-integration-backups`, removes only
   the old Member 3 registrations, then wires the extracted modules. Running it
   again is safe. A different shared baseline causes it to stop for manual review.
4. Inspect `integration/member3_backend.patch`. Do not add a second registration
   beside the original handlers: that would produce duplicate Flask endpoints.
5. Install the full baseline dependencies, run the isolated tests, then rebuild
   the full React application. See the commands below.

The three React pages remain byte-for-byte compatible with the verified baseline.
Their imports resolve through shared `AuthContext`, `WorkspaceUI`, `ExperienceUI`,
the API utility, React Router and Recharts supplied by the complete application.
No login or RTO pages are replaced by this submission.

## API contract

| Endpoint | Roles | Purpose |
|---|---|---|
| `GET /api/overview` | USER/RTO/ADMIN/GOVT | Scoped totals, trends and recent summaries |
| `GET /api/case-filters` | USER/RTO/ADMIN/GOVT | Recorded location/type choices |
| `GET /api/cases` | USER/RTO/ADMIN/GOVT | Paginated, scoped case register |
| `GET /api/cases/<id>` | USER/RTO/ADMIN/GOVT | Role-filtered case details |
| `GET /api/gov/analytics` | GOVT/ADMIN/RTO | Existing compatible aggregate report |
| `GET /api/admin/users` | ADMIN | Paginated account administration |
| `PATCH /api/admin/users/<id>` | ADMIN | Role assignment with reason/revocation |
| `GET /api/admin/audit` | ADMIN | Paginated audit history |
| `GET/PUT /api/admin/policy` | ADMIN | Read/update the versioned project fine policy |
| `GET /api/operator/health` | ADMIN/RTO | Worker/model/queue/session status |

Overview/register filters include `scope`, `status`, `type`, `location`, `camera`,
`q`, `from` and `to`. Dates supplied by the UI are UTC instants derived from IST
calendar boundaries. Case search supports the displayed `EM-` reference.
Case-list pagination uses `page` and `size` (bounded on the server).

The shared Flask authentication/authorization helpers are reused. This module
does not create a separate identity system, trust browser-stored roles or expose
the database directly to the frontend.

## Running the integrated college project

Use Python 3.14 and Node 24 with the complete baseline. From its root:

```powershell
.\scripts\setup.ps1
# Optional local fictional demonstration records/accounts:
.\.venv\Scripts\python.exe -m scripts.seed_showcase
.\scripts\start.ps1 -Rebuild
```

Open http://127.0.0.1:3001; the API uses port 5000. Only one copy should use these
ports on a single computer. The baseline's `START_PROJECT.cmd` is the normal
subsequent-start shortcut. Demo credentials are generated privately during local
seeding; they are not committed or included here.

### Testing after integration

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/test_member3.py -q
.\.venv\Scripts\python.exe -m pytest tests -q
```

On Windows, a workspace test directory can be supplied with
`--basetemp=data/member3-test-check`. Tests use isolated databases/storage and do
not use the running application's real records. Validation results and exact
integration context are recorded in `docs/VALIDATION.md`.

## College scope and limitations

The full project demonstrates evidence -> RTO review -> memo -> verified citizen
payment/dispute -> government analytics. RTO officers confirm cases. Fine amounts
follow a project policy; payments are sandbox records and owner notices are previews.
Dataset registration/owner assignments are fictional.

Automatic specialist helmet/rider enforcement, official registration lookups,
real payment collection and public hosting are outside this college release.
The report describes the integrated team project; this upload's source ownership
is limited to the Member 3 scope and shared support files listed above.

## Provenance

The working college baseline derives from
https://github.com/prekshagohel29/traffic_violation_system with subsequent local
evidence-workflow and college-polish work. See `THIRD_PARTY_NOTICES.md`. Preserve
its original attribution, model/dataset notices and dependency licences when the
team merges and distributes the complete application.

No local passwords, `.env`, live database, private evidence, installed dependencies,
model weights, test photos or fabricated contributor history are part of this upload.
