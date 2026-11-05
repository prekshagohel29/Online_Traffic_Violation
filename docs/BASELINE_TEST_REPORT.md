# College release verification · 5 November 2026

| Check | Executed result |
|---|---|
| Backend regression | 31 passed; artifacts/backend-tests.xml |
| Case/search follow-up including lowercase references | 5 passed |
| React unit test | 1 passed |
| Edge browser workflows | 11 passed, no skips/flaky results; artifacts/browser-report.json |
| QA and final local React builds | Both passed; final API origin is http://127.0.0.1:5000 |
| Python compilation | Passed |

Browser verification used the workspace's isolated data/browser-qa database on
ports 3101/5100. It did not seed or reset the user's saved current-build database.
The previous-build folder, credentials and ZIP were not changed by this release.

## Executed behavior

- Citizen signup persists and can log in again; logout/direct-route refresh work.
- Stale browser roles cannot grant administrator access; server roles and ownership
  restrict memos/evidence. Government summaries redact identifying details.
- Dataset evidence -> RTO confirmation -> linked memo -> correct citizen sandbox
  payment -> PDF receipt -> government summary passes in the browser.
- Real included-video and uploaded-video jobs run vehicle inference, save private
  evidence and open a reviewable case. The test follows the newly submitted job.
- Recorded camera frames are processed; Stop releases tracks and permission denial
  is visible. Session previews cannot show a different session's previous image.
- Layout checks at 360, 768 and 1440 pixels pass, including horizontal page width.
- The college video selector contains webcam/upload inputs; the research comparison
  is absent. Camera thresholds are collapsed and service status is readable.
- Displayed EM- references can be searched without bypassing ownership. Lowercase
  reference search also passes the targeted backend follow-up.
- Analytics has location/type choices, date validation and Clear filters.
- Review/payment idempotency, disputes, queue recovery/backpressure, calibration
  invalidation, rule boundaries, legacy migration and rollback are checked.
- The removed classifier-analysis and inactive reset endpoints return 404.

## Defined college scope

The final application demonstrates AI-assisted vehicle/movement review, manual
evidence review, verified ownership, project memos, sandbox receipts, disputes,
anonymized oversight and administrator controls. RTO officers confirm cases.
Published helmet labels are used for manual dataset exercises.

Automatic specialist helmet/rider/seatbelt/phone enforcement, automatic traffic-light
recognition, external camera gateways, official registry/payment integrations and
public hosting are outside this college release. They are not advertised by
unfinished controls. Password support is administrator-managed. Notices are previews.

Passing workflow tests does not establish field recognition accuracy. The model
sources, detector timing and research limits are retained in MODEL_SETUP.md.
No test sent real email, charged money or accessed the friend's database.

## Preservation and academic handoff

The current saved database/evidence are retained in place during the code update.
A SQLite backup and previous changed files are stored under saved-backups.
PRESERVATION_MANIFEST.json identifies the verified source/build and backup folder.

COLLEGE_COMPLETION_CHECKLIST.md describes the final feature decisions;
COLLEGE_PROJECT_REPORT.md supplies the report/architecture/database/viva content;
DEMO_GUIDE.md supplies the examiner walkthrough. The student can add the institution's
cover-page details and rehearse or record the demonstration as required.
