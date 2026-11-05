# Upload all three final packages

The original Member_1/2/3 folders are complete runnable copies for local work.
For GitHub, use the dedicated Member_1_GitHub_Upload, Member_2_GitHub_Upload and
Member_3_GitHub_Upload folders. Upload each folder's CONTENTS at repository root.
Keep subdirectories intact. Do not upload the wrapper folder or a ZIP file.

## Order

1. **Member 3 first**: government/admin modules, shared models/db/migrations, docs
   and test fixture. If this is already on GitHub, leave it there.
2. **Member 1 next**: citizen/auth pages and the complete shared integration shell.
   Its README.md replaces the initial Member 3-only README with the final team
   README. Its .gitignore extends the initial ignore rules for generated assets.
3. **Member 2 last**: RTO/video/worker modules, source tests, licensed samples and
   smaller plate models. No existing source files need replacing in this step.

Only README.md and .gitignore overlap with differing content (Member 1 intentionally
updates them). All other package paths are disjoint. Shared app.py/experience.py
are supplied by Member 1 already integrated with Member 3, so no manual code merge
or additional route registration is needed for this release. Keep Member 3's
integration files for reference; its helper remains safe to rerun.

For each upload: open the repository in the correct member's GitHub account,
select Add file > Upload files, drag everything INSIDE that member's upload
folder into the upload area, wait for completion, inspect filenames and commit.
For an empty repository, use the 'uploading an existing file' link first.

Suggested commit messages:
- Member 3: Add government, administration and reporting modules
- Member 1: Add citizen portal, authentication and shared app integration
- Member 2: Add RTO evidence review, video analysis and licensed sample assets

Members 1 and 2 need collaborator/write access before uploading to the shared
repository from their accounts, or they can contribute via forks and reviewed pull
requests. Each member should commit their genuine work from their own account.
Do not change authors or manufacture equal commit histories.

Each package has fewer than 100 files and every file is under 25 MiB, so one browser
upload per package is sufficient. The large YOLOX model is downloaded and checked
by setup. ZIPs are convenient for sharing; extract them before uploading.

## Final check

Download the completed repository to a NEW folder. From its root run:

    python scripts/verify_team.py
    python integration/apply_member3.py

The first reports missing modules if an upload was incomplete; the second should
say integration is already applied. Then run SETUP_MEMBER.cmd, optionally
LOAD_DEMO_DATA.cmd and START_PROJECT.cmd. Read the root README for all commands.
The final app serves at http://127.0.0.1:3001 and keeps its private data locally.

Do not copy the old complete Member_1/2/3 folders over this integrated release.
They contain the unextracted baseline backend and would undo Member 3 registration.
Keep this final GitHub repository as the shared source of future team edits.
