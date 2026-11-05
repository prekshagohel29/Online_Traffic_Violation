# College demonstration: evidence to resolution

Open http://127.0.0.1:3001 and use LOCAL_TEST_ACCOUNTS.md for the local logins.
Start with this explanation: "This is an AI-assisted review and e-Memo management
system. Video analysis flags possible events; an RTO officer confirms the case."

## Suggested 7-minute demonstration

1. **RTO overview (30 seconds).** Show the workflow, saved totals and source filter.
2. **Dataset case (1 minute).** Open Dataset examples, choose a helmet photograph,
   and create a practice case. Explain that its source labels are published dataset
   annotations and that the displayed scooter/owner is fictional. Inspect the
   image and ownership card, give a reason, acknowledge review, and confirm.
3. **Citizen receipt (1 minute).** Sign out and sign in as Vehicle Owner. Find the
   new GJ00DM1010 memo, open its evidence, record a sandbox payment and download
   the PDF receipt. Explain that no real money moves.
4. **Dispute (1 minute).** Use a different unpaid memo. Submit a citizen explanation,
   then sign in as RTO and open Reviews & requests -> Disputes. Resolve it with a
   reason. An upheld dispute cancels the memo; a dismissed dispute restores unpaid.
5. **Actual video (1 minute).** In Video analysis press Analyse included traffic
   video. Show the original clip, analysed timestamped preview and completed job.
   Open a flagged case. Explain that the sample zone is a configured practice zone,
   rather than an assertion that a driver committed an actual offence. Processing
   may take 30-60 seconds; use that interval to describe the rule and review stage.
6. **Government analytics (1 minute).** Switch roles. Choose a location or violation
   type, change the date range, clear filters, and compare Demo examples with
   Recorded cases. Open a case summary to show that private identity/evidence is hidden.
7. **Administration (30 seconds).** Show service readiness, the project fine policy
   and the audit trail. Explain that only an administrator grants staff roles.
8. **Persistence (30 seconds).** Reload a case and show that its decision/receipt
   remains saved. START_PROJECT.cmd reuses the same database after a normal restart.

## Optional ownership explanation

Citizen vehicle requests remain pending until the RTO verifies them. Typing a plate
alone gives no access. Use the fictional pending example if available; never claim
that a demonstration approval is a real government registration lookup.

## Useful facts for questions

- The frontend is React; Flask/Python provides the API and video worker.
- Vehicle detection uses a checksummed pretrained YOLOX model. Configured movement
  rules create candidates, while officers can also enter manual observations.
- Evidence images are private, and citizen access depends on approved ownership.
- Fine amounts follow a project policy. Sandbox receipts and notice previews are
  intentional demonstration features.
- Automatic helmet/rider-count enforcement and official registry/payment access
  are outside this release. The interface does not advertise unfinished controls.

Report material: COLLEGE_PROJECT_REPORT.md. Feature decisions and final checks:
COLLEGE_COMPLETION_CHECKLIST.md and TEST_REPORT.md.
