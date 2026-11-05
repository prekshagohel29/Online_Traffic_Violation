# Ordered migrations

1. Fresh PostgreSQL: run `001_schema.sql`, then `002_private_access.sql`.
   Local SQLite: `python -m backend.manage init` creates the same versioned tables.
2. Supabase: run `003_supabase_storage.sql`; inspect/remove any old permissive
   storage policies before uploading private evidence.
   Run `004_casebook.sql` for the additive vehicle-profile/dataset/case-metadata
   upgrade; it also applies private access restrictions to the added tables.
3. Upgrade: back up a COPY of the original database; initialize the versioned tables;
   run `python -m backend.manage import-legacy` against that copy and verify counts.
   The importer is transactional and idempotent (`legacy_import_v1` marker).
4. Only after review, run the same non-destructive process against your authorized
   production database. Never rerun the superseded backend/migrate*.sql scripts.

Original tables are retained. Original user/violation/memo IDs are copied as strings;
candidate IDs use `legacy-<violation-id>`. `fine` and `memo` are reconciled to one
issued memo per violation. Conflicting duplicate source records remain in audit
JSON and original tables. `PAID` without provider evidence becomes
`LEGACY_UNVERIFIED`; it is not revenue. Old ownership links require reverification.
Known `@system.com` demo accounts are disabled, including their password hashes.
Passwords for real imported users remain hashed exactly as before; old tokens are invalid.

Rollback: redeploy the prior application only against a restored database copy;
do not reopen anonymous access or rerun destructive rename scripts. The new code
does not drop historical tables. Never restore an old application publicly with
the known vulnerabilities enabled.
