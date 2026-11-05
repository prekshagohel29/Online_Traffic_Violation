# Source formatting

This maintenance change expands compressed Python and React source into
consistent, readable blocks. Selected JavaScript files and JSON use four-space
indentation and an 88-column target; Python uses Black's standard 88-column style. Dataset
annotation JSON is expanded so individual records can be inspected and reviewed.
Dependency versions and annotation values remain unchanged.

No UI, application behavior, permissions, database schema or user flow is changed.
This commit records formatting and the authorship documentation, not new features
or a rewrite of earlier commits.

## Reproducing the style

Use Black 26.10.1 for the tracked Python source and Prettier 3.9.10 for the tracked
JavaScript and JSON files, using the repository's `.prettierrc.json`. Formatting
tools are development utilities and are not added to application dependencies.

The release fingerprints in `integration/team_release.json` and the completed
Member 3 integration fingerprints are updated to match the formatted source.
Existing third-party licenses and provenance are retained.

## Verification

Python syntax trees must match before and after formatting. React source is
transformed with the same JSX compiler before comparing JavaScript syntax trees;
this checks JSX whitespace semantics as well as executable code. Eight React
files are preserved because formatting would change their JSX child structure;
they are listed in `.prettierignore`. JSON values, including the entire npm
dependency lock and dataset annotations, must compare
equal. CSS, static images, video, model weights and database migrations are
unchanged byte-for-byte. Run the backend tests, React tests, production build and
strict team integration checks after formatting.
