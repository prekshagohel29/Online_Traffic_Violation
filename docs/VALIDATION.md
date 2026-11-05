# Member 3 validation

The extracted Government/Admin/reporting modules were overlaid onto a separate
copy of the complete verified college baseline. The integration helper was applied
twice: the first run rewired only Member 3 registrations, and the second was a no-op.

- **36 backend checks passed**, zero failures/errors/skips (31 existing + 5 new).
- Full original/integrated API maps match: **65 route registrations**,
  including paths, methods and Flask endpoint names.
- All three Member 3 React pages are byte-identical to the working baseline.
- Original Member 1, Member 2 and Member 3 package manifests still verify.
- No live application database, private evidence, credentials or existing member
  folders were changed. Tests used isolated workspace databases/storage.

## New member-specific checks

1. Scoped totals, location/type/source filtering and IST day grouping.
2. Government redaction and citizen ownership isolation.
3. Trusted role assignment, old-session revocation and self-role-change protection.
4. Fine-policy validation/versioning and audit records.
5. Compatible government reporting and protected service status.

## Commands executed against the integrated full baseline

```text
python integration/apply_member3.py
python integration/apply_member3.py
python -m compileall -q backend integration
python -m pytest tests -q --basetemp=<isolated workspace directory> --junitxml=<report>
```

The full baseline's existing React build and 11 browser workflows are documented
separately in BASELINE_TEST_REPORT.md. This preparation did not rerun those browser
checks or claim that the partial Member 3 repository is a standalone application.
No GitHub publication is implied by this local validation report.
