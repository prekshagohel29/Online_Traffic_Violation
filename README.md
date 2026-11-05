# Online Traffic Violation — e-Memo

A college project developed by **Preksha Gohel (Member 3)** for reviewing traffic
evidence and managing project memos. **React is the only frontend framework**. A Flask API, SQLAlchemy
database and CPU video worker support the four role portals.

## What the completed team project does

- **Citizen:** registration/login/profile, verified vehicle-link requests, private
  owned memos/evidence, PDF receipts, sandbox payments and dispute submission.
- **RTO:** case register, evidence review, camera calibration, uploaded-video and
  webcam processing, vehicle/ownership review, memo issuance and dispute decisions.
- **Government:** anonymized oversight, recorded location/type/source/date filters,
  charts and totals from the same saved cases.
- **Administrator:** trusted staff roles, versioned fine policy, audit history and
  readable service/worker status.

Real YOLOX detection/tracking supports configured experimental movement flags.
An RTO reviews evidence before confirming a case. Public dataset examples have
explicitly fictional owner associations. Payments transfer no money; notices are
local previews. This is a college demonstration, not an official enforcement service.

## Project authorship

**Preksha Gohel — primary developer and project lead.** The project owner
identifies Preksha as the original developer of the application. See
[AUTHORS.md](AUTHORS.md) for the authorship and third-party credit statement.

The repository was delivered using three member upload packages. Those package
boundaries describe how files were submitted; they do not establish who
originally wrote every file.

## Upload packages and files

| Upload member | Packaged area | Guide |
|---|---|---|
| 1 | Citizen/authentication and delivery of shared app shell/core | [Member 1](MEMBER_1_README.md) |
| 2 | RTO, evidence, camera/video, worker/models and dataset assets | [Member 2](MEMBER_2_README.md) |
| 3 | Government/Admin, reporting, audit, database and college report | [Member 3](docs/TEAM_OWNERSHIP.md) |

Shared routing, authentication utilities, database contracts and reusable UI are
team infrastructure. Delivery ownership does not reassign authorship of existing
source. Preserve upstream/model/dataset credits and commit genuine changes using
each contributor's own GitHub account.

## Upload and integration status

The repository is runnable **after all three upload packages are merged at its
root**. An individual package is a contribution to the application, not a separate
standalone app. Read [TEAM_UPLOAD_GUIDE.md](TEAM_UPLOAD_GUIDE.md).

Upload in this order: **Member 3, Member 1, Member 2**. Member 1 supplies this final
team README and the common launch files. If Member 3 is already uploaded, continue
with Member 1 and Member 2. Do not nest the upload package folder inside the repo.
The Member 1 shared backend is already wired to Member 3's extracted modules;
running `python integration/apply_member3.py` again is a no-op on this release.

## Fresh installation on Windows

Tested with Python 3.14 and Node.js 24. Internet is needed for dependency setup
and the checksummed 35,858,002-byte YOLOX model. Smaller licensed models and the
sample footage/photos are already included by Member 2. No passwords, live
database, private evidence or installed dependencies are included.

1. Download/extract or clone the complete repository.
2. Run `python scripts/verify_team.py` to check that all modules were uploaded.
3. Double-click **SETUP_MEMBER.cmd** once. It installs dependencies, creates local
   settings/database and downloads/verifies the model.
4. Optionally run **LOAD_DEMO_DATA.cmd** for fictional examples and fresh local
   role accounts. Read the generated **LOCAL_TEST_ACCOUNTS.md** for their logins.
5. Run **START_PROJECT.cmd** and open **http://127.0.0.1:3001**.

Keep the terminal open. The first start builds React from the supplied source.
The API uses port 5000. Run one copy at a time on the same machine. Local accounts,
cases and evidence persist in `data/`; restarting does not reset them.

Without demo data, provision an administrator locally:

```powershell
.\.venv\Scripts\python.exe -m backend.manage provision --email you@example.com --role ADMIN --name Administrator
```

Public signup creates citizens only. Other staff accounts require trusted
provisioning. Never upload the generated `.env`, `data/` or login files.

## Development and verification

```powershell
python scripts/verify_team.py --strict
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
npm --prefix frontend test -- --watchAll=false --runInBand
powershell -ExecutionPolicy Bypass -File scripts/start.ps1 -Rebuild
```

`--strict` compares release fingerprints; expected hashes change after deliberate
edits. `--ready` also requires the downloaded YOLOX asset. Test data stays isolated
from the live local app. Browser verification instructions and the final combined
test results are in [docs/FINAL_TEAM_VALIDATION.md](docs/FINAL_TEAM_VALIDATION.md).

## College report and model scope

- [College project report](docs/COLLEGE_PROJECT_REPORT.md)
- [Completed college scope](docs/COLLEGE_COMPLETION_CHECKLIST.md)
- [Demonstration guide](docs/DEMO_GUIDE.md)
- [Architecture](ARCHITECTURE.md)
- [Models, data and measured limits](MODEL_SETUP.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

Arbitrary-camera accuracy, automatic helmet/phone/seatbelt enforcement, official
registration/payment connections and a public deployment are outside this college
release. Research classifier code/weights are retained for provenance, with its
comparison UI/API disabled. Human review remains required for project memos.
