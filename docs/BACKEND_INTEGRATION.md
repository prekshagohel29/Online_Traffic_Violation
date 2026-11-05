# Backend integration

The complete shared core must be present before running this module. The helper
checks the exact two baseline hashes and retains backups before changing files.
It moves Member 3 registrations into member3_admin/member3_reporting and retains
the existing authentication, citizen mutations, RTO review, video/evidence, CSV
export and owner-notice handlers. Reporting returns its profile helper for the
remaining registry handlers so their existing data contract is preserved.

Run `python integration/apply_member3.py` from the complete repository root.
A second run is a no-op. If the core files have changed, inspect the supplied
patch and merge manually rather than overwriting another member's work.

The frontend depends on the complete app's API utility, authentication context,
WorkspaceUI, ExperienceUI, common CSS, React Router and Recharts. Merge the app
shell and other role pages from the baseline; keep these three pages at their
original paths. Do not add a second Member 3 route registration beside the old one.
