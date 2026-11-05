# Member 2 — RTO, evidence and video analysis

This upload completes the shared application with RTO screens, the durable video
worker, detector/tracker/rules, plate runtime and licensed sample assets. Upload
its CONTENTS at the repository root after Members 3 and 1. See docs/MEMBER_2_UPLOAD.md.

## Delivered workflows

- RTO overview, manual reports, case register, evidence and vehicle directory.
- Uploaded-video jobs with progress/results, browser webcam control and calibration.
- Real YOLOX vehicle detection/tracking with configured experimental movement flags.
- Pending case review and explicit evidence acknowledgement before memo issuance.
- Vehicle ownership approvals, dispute decisions and attributed dataset practice.

## Main files

- RTO pages: `Overview`, `RTODashboard`, `Monitor`, `Calibration`, `Evidence`,
  `Casebook`, `CasePage`, `DatasetLibrary`, `Registry`.
- `backend/worker.py`, `vision.py`, `rules.py`, `plates.py`, `camera_sources.py`.
- Licensed plate models/configuration, sample footage, attributed practice images
  and reproducible asset fetchers. Original model/dataset credit is retained.
- Baseline video/recovery/rules/plate/camera/experience tests and browser workflows.
- Research `helmet.py`/training artifacts are provenance material, not an active
  automatic helmet-enforcement feature. The college UI/API do not expose it.

RTO route registrations in `backend/app.py` and dataset/registry operations in
`backend/experience.py` are shared core delivered once in Member 1. Do not replace
those files with the older original member-folder versions. Member 3 supplies
models/db/reporting code and fixtures. This partial upload is not standalone.

## Large model and browser uploads

All supplied files fit GitHub's browser upload size. The 35,858,002-byte YOLOX file
is intentionally provisioned by **SETUP_MEMBER.cmd**, using `scripts.fetch_assets`
and the original pinned checksum. It is not included in this upload or its ZIP.
SHA-256: `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`.
After setup the model is exactly the working baseline model. Other required
licensed plate models, the CC0 video and practice images are bundled.

## Demonstration and checks

After merging all members, follow the root README. Demonstrate the included clip,
inspect a completed job and pending evidence, acknowledge review, confirm a project
memo, approve an ownership link and decide a dispute. Webcam Stop must release
camera tracks. Uncalibrated motion and model scores never prove an offence or owner.

The combined suite and browser commands/results are in docs/FINAL_TEAM_VALIDATION.md.
Model/data limitations are in MODEL_SETUP.md; licenses and notices accompany the
assets. Do not publish local evidence, camera credentials, accounts or runtime data.
Commit genuine work from your own account and preserve existing source credit.
