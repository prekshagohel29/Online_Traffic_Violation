-- 004: additive casebook/showcase upgrade. Does not replace existing records.

BEGIN;


CREATE TABLE IF NOT EXISTS tv_vehicle_profiles (
	id VARCHAR(25) NOT NULL,
	model VARCHAR(120) NOT NULL,
	vehicle_class VARCHAR(30) NOT NULL,
	color VARCHAR(40) NOT NULL,
	registration_reference VARCHAR(100) NOT NULL,
	owner_display_name VARCHAR(150) NOT NULL,
	contact_phone VARCHAR(30) NOT NULL,
	address VARCHAR(300) NOT NULL,
	is_demo INTEGER NOT NULL,
	created_at VARCHAR(40),
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS tv_dataset_assets (
	id VARCHAR(100) NOT NULL,
	title VARCHAR(180) NOT NULL,
	category VARCHAR(80) NOT NULL,
	source_url TEXT NOT NULL,
	license VARCHAR(100) NOT NULL,
	attribution TEXT NOT NULL,
	object_key VARCHAR(240) NOT NULL,
	sha256 VARCHAR(64) NOT NULL,
	annotations JSON NOT NULL,
	created_at VARCHAR(40),
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS tv_case_metadata (
	id VARCHAR(60) NOT NULL,
	is_demo INTEGER NOT NULL,
	asset_id VARCHAR(100),
	note TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(id) REFERENCES tv_candidates (id),
	FOREIGN KEY(asset_id) REFERENCES tv_dataset_assets (id)
)

;

CREATE INDEX IF NOT EXISTS ix_tv_case_metadata_is_demo ON tv_case_metadata (is_demo);

COMMIT;

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
