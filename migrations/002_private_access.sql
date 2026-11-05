-- Run AFTER 001 on Supabase as the database owner, then use a server-only DB role.
-- Flask JWTs are not Supabase Auth tokens: browsers receive no direct table access.
BEGIN;
DO $$ DECLARE t record; r text; BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public'
    AND (tablename LIKE 'tv_%' OR tablename IN ('users','vehicle','violation','memo','fine','payments','user_vehicles'))
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',t.tablename);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC',t.tablename);
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r) THEN
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I',t.tablename,r);
      END IF;
    END LOOP;
  END LOOP;
END $$;
COMMIT;
