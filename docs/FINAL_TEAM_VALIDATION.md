# Final combined team verification

This check assembled a fresh application from the actual upload packages in this
order: existing Member 3, final Member 1, final Member 2. It did not copy missing
application code from the full working build. The main YOLOX asset was provisioned
through the actual pinned downloader's missing-file branch, with the exact cached
public model supplied as its download response. Live download availability was
not tested; fresh setup needs internet for dependencies and that model.

## Results

- **36 backend tests passed**, with no failures/errors/skips (31 baseline + 5 Member 3).
- **1 React unit test passed** and the optimized production React build succeeded.
- **11 browser workflows passed** against the assembled app, including signup/login,
  citizen restrictions, responsive screens, webcam error/stop behavior, actual frame
  analysis, upload/results, dataset-to-memo-to-citizen payment/PDF, sample-video
  processing, searchable cases, government filters/privacy and administrator status.
- **65 API registrations match** the original baseline by path, method and endpoint.
- All **43 frontend source files**, six public assets, 24 sample files, ten model
  files (after provisioning) and 14 unmodified shared/backend support files match
  the baseline byte-for-byte. Only shared app.py/experience.py were rewired to
  Member 3's already-tested extracted modules; their accepted after-hashes match.
- Member 3 integration helper was run twice; both runs safely reported already
  integrated. Missing-module checks reject an incomplete upload before setup.
- Original Member_1/2/3 working folders and the existing Member 3 upload stay unchanged.

Private tests used separate local storage and ports 3003/5003. The delivered start
script retains normal ports 3001/5000. No live user data was used or modified.
Private QA accounts, databases, screenshots, dependencies and generated builds
are excluded from the upload packages. No GitHub publication is implied.

## Reproduce after merging the three uploads

```powershell
python scripts/verify_team.py --strict
python integration/apply_member3.py
```

Run SETUP_MEMBER.cmd. Then:

```powershell
.\.venv\Scripts\python.exe scripts/verify_team.py --strict --ready
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
npm --prefix frontend test -- --watchAll=false --runInBand
```

For isolated browser testing, build with the QA API address (5003), load fixtures
into data/browser-qa, start the QA harness, then run Playwright. Use separate
terminals for the server and tests. From the repository root:

```powershell
$env:REACT_APP_API_BASE_URL='http://127.0.0.1:5003'
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m scripts.seed_showcase --data-dir data/browser-qa
.\.venv\Scripts\python.exe -m scripts.qa_server --web-port 3003 --api-port 5003
```

In another terminal, open frontend, then:

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:3003'
$env:E2E_API_URL='http://127.0.0.1:5003'
npm run test:browser
```

Browser tests use installed Microsoft Edge and generated fake-camera footage.
Stop the QA server afterwards. Before using the ordinary local app again, rebuild
for its normal API with `powershell -ExecutionPolicy Bypass -File scripts/start.ps1 -Rebuild`.
The same steps were executed during final package verification.
