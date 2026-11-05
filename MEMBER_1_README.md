# Member 1 — Citizen and authentication

This upload contains the citizen/authentication screens and the shared application
shell needed to connect all three members' modules. Upload its CONTENTS at the
repository root, after Member 3 and before Member 2. See TEAM_UPLOAD_GUIDE.md.

## Delivered workflows

- Public citizen registration, login/logout, token/session checks and profile.
- Vehicle ownership-link requests and access limited to verified ownership.
- Own memo search, private evidence and PDF memo/receipt downloads.
- Sandbox payment with duplicate protection and citizen dispute submission.

## Main files

- `frontend/src/pages/Auth.js`, `RoleSelection.js`, `UserDashboard.js`, `UserProfile.js`
  and their styles.
- `frontend/src/context/AuthContext.js`, protected routing, API utilities and
  reusable components/styles: shared dependencies maintained with the team.
- `frontend/src/App.js`, package/lock files and public assets: shared React shell.
- `backend/app.py`, `backend/experience.py`, `backend/storage.py`: shared core that
  contains citizen handlers plus retained RTO integration routes. Member 3's moved
  reporting/admin handlers are registered from its extracted files, without duplicates.
- Setup/start/demo scripts, dependency locks and complete-repository checks.
- `tests/test_security_workflow.py`, `tests/test_migration.py`: baseline shared
  security/workflow and migration coverage; attribution remains unchanged.

## Dependencies on teammates

Member 2 supplies the RTO/worker/rules/video modules and remaining role pages.
Member 3 supplies database definitions, government/admin/reporting modules, test
fixtures and college documentation. Do not run this partial folder by itself.
The common backend is already at the after-hashes accepted by Member 3's helper.

## Running and explaining your work

After all packages are merged, run SETUP_MEMBER.cmd, optionally LOAD_DEMO_DATA.cmd,
then START_PROJECT.cmd. Demonstrate a citizen registering, requesting a vehicle
link, receiving RTO approval, viewing only owned memos, recording a sandbox receipt
and disputing an unpaid memo. Explain role checks, ownership checks, private
evidence and duplicate-payment protection. Public signup must never create staff.

Use the root README for complete setup, checks and privacy rules. The final
combined validation is in docs/FINAL_TEAM_VALIDATION.md. The package contains no
saved logins/private database. Record actual review, testing and subsequent code
changes; responsibility guides do not manufacture past authorship.
