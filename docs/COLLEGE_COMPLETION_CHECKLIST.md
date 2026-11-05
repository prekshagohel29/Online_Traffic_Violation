# College-project completion checklist

Project: **AI-assisted Traffic Violation Review and e-Memo Management**.

The finished college scope is a working local application with a clear evidence
and review process. The retained features below form the demonstration and report.

## 1. Keep the complete case journey

- Citizen registration/login, profile changes and administrator-managed staff roles.
- Verified vehicle ownership before a citizen can read private cases or images.
- Video vehicle detection/tracking and configured movement-rule candidates.
- Authenticated manual reports and attributed dataset practice cases.
- RTO confirmation, rejection or request for more evidence, with a recorded reason.
- One linked project memo per confirmed case, downloadable as a PDF.
- Sandbox payment receipts and citizen disputes with RTO resolution.
- Government totals/charts from the same saved records, with private identities hidden.
- Administrator role management, project fine policy, service status and audit history.

Completion evidence: isolated backend checks and the full browser case journey.

## 2. Finish the small usability gaps

- Search by the EM- case reference displayed in the register.
- Provide actual location/type choices for analytics, with clear/resettable date filters.
- Reject an end date earlier than the selected start date in the screen.
- Keep direct links to demonstration cases consistent with the selected source filter.
- Use readable review/ownership status labels.
- Keep advanced camera coordinates and thresholds collapsed until needed.
- Show the original included video beside its analysed preview.
- Reset webcam counters for each new session and avoid showing another session's frame.
- Keep owner privacy, sandbox labels and dataset attribution visible where relevant.

Completion evidence: reference/ownership/filter backend tests and dedicated browser checks.

## 3. Remove unfinished-looking product controls

- Remove the research head-classifier comparison button and its HTTP endpoint.
- Remove the unconfigured external IP-camera choice from the college interface.
- Remove the inactive self-service password-reset endpoint and its “not configured” message.
- Show useful processing status instead of a paragraph listing missing specialist models.
- Present notices as saved owner-notice previews; do not advertise unconfigured email delivery.

Account support remains an administrator task. The trusted local recovery command
is `python -m backend.manage recover --email account@example.com`; it prompts for
a replacement password. Public self-service recovery is outside this release.

Research source artifacts and deployment documentation may remain for reference.
They are outside the college demonstration and are not advertised as completed features.

## 4. Define the project honestly

- Video analysis detects vehicles and evaluates configured movement rules.
- RTO officers make the final case decision and review uncertain plate readings.
- Helmet dataset images support manual review exercises; they are not proof of
  automatic helmet or rider-count recognition by this application.
- Payments are sandbox records. Notices are previews. Fine amounts follow a project policy.
- Example owners and registration associations are fictional.

Automatic helmet/triple-riding/seatbelt/phone-use enforcement, automatic traffic-light
recognition, official registry connections, real payment collection and public hosting
are excluded from this college release. They are optional future extensions.

## 5. Make the submission easy to explain

- `COLLEGE_PROJECT_REPORT.md`: purpose, objectives, modules, architecture, tables,
  workflow, implementation, testing, limits and viva talking points.
- `DEMO_GUIDE.md`: a short, repeatable examiner demonstration.
- `TEST_REPORT.md`: executed checks and the exact limits of those results.
- `START_PROJECT.cmd`: normal local startup. Accounts/data persist across restarts.
- `LOCAL_TEST_ACCOUNTS.md`: private local credentials for switching roles.
- The existing old-build folder/ZIP remain a separate preserved version.

## 6. Final review before submission

Run one paid example and a separate disputed example, download their PDFs, switch
roles, inspect analytics, and restart the application. Include a real video run
to show that vehicle analysis is genuine. Check the demo on a phone-sized screen.

The student-specific tasks are to add the institution's required cover page,
student/guide details and formatting, then rehearse the demonstration. A recorded
demo can be captured if the institution asks for one. These presentation choices
do not require adding more application features.
