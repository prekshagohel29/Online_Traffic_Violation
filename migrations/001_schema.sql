-- 001: versioned schema; existing legacy tables are not altered.

BEGIN;


CREATE TABLE IF NOT EXISTS tv_audit (
	id VARCHAR(60) NOT NULL,
	actor VARCHAR(60) NOT NULL,
	action VARCHAR(100) NOT NULL,
	target VARCHAR(100) NOT NULL,
	details JSON NOT NULL,
	created_at VARCHAR(40),
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS tv_cameras (
	id VARCHAR(60) NOT NULL,
	name VARCHAR(100) NOT NULL,
	location VARCHAR(150) NOT NULL,
	source_key VARCHAR(100),
	config JSON NOT NULL,
	version INTEGER NOT NULL,
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


CREATE TABLE IF NOT EXISTS tv_rate_limits (
	id VARCHAR(100) NOT NULL,
	count INTEGER NOT NULL,
	"window" FLOAT NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS tv_revocations (
	id VARCHAR(60) NOT NULL,
	expires FLOAT NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS tv_services (
	id VARCHAR(60) NOT NULL,
	heartbeat FLOAT NOT NULL,
	details JSON NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS tv_settings (
	id VARCHAR(100) NOT NULL,
	value JSON NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS tv_users (
	id VARCHAR(60) NOT NULL,
	email VARCHAR(255) NOT NULL,
	password_hash TEXT NOT NULL,
	role VARCHAR(10) NOT NULL,
	full_name VARCHAR(150) NOT NULL,
	phone_number VARCHAR(30),
	last_login VARCHAR(40),
	token_version INTEGER NOT NULL,
	active INTEGER NOT NULL,
	PRIMARY KEY (id),
	CHECK (role IN ('USER','RTO','GOVT','ADMIN')),
	UNIQUE (email)
)

;


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


CREATE TABLE IF NOT EXISTS tv_devices (
	id VARCHAR(60) NOT NULL,
	camera_id VARCHAR(60) NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	active INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(camera_id) REFERENCES tv_cameras (id)
)

;


CREATE TABLE IF NOT EXISTS tv_ownership (
	id VARCHAR(60) NOT NULL,
	user_id VARCHAR(60) NOT NULL,
	plate VARCHAR(25) NOT NULL,
	status VARCHAR(20) NOT NULL,
	proof TEXT NOT NULL,
	reason TEXT,
	reviewer VARCHAR(60),
	created_at VARCHAR(40),
	PRIMARY KEY (id),
	UNIQUE (user_id, plate),
	FOREIGN KEY(user_id) REFERENCES tv_users (id)
)

;

CREATE INDEX IF NOT EXISTS ix_tv_ownership_plate ON tv_ownership (plate);


CREATE TABLE IF NOT EXISTS tv_sessions (
	id VARCHAR(60) NOT NULL,
	user_id VARCHAR(60) NOT NULL,
	camera_id VARCHAR(60) NOT NULL,
	kind VARCHAR(20) NOT NULL,
	status VARCHAR(30) NOT NULL,
	config JSON NOT NULL,
	calibration_version INTEGER NOT NULL,
	last_seq INTEGER NOT NULL,
	last_ts FLOAT NOT NULL,
	heartbeat FLOAT NOT NULL,
	received INTEGER NOT NULL,
	dropped INTEGER NOT NULL,
	processed INTEGER NOT NULL,
	result JSON NOT NULL,
	preview_key VARCHAR(200),
	state JSON NOT NULL,
	created_at VARCHAR(40),
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES tv_users (id),
	FOREIGN KEY(camera_id) REFERENCES tv_cameras (id)
)

;


CREATE TABLE IF NOT EXISTS tv_candidates (
	id VARCHAR(60) NOT NULL,
	event_key VARCHAR(200) NOT NULL,
	session_id VARCHAR(60),
	camera_id VARCHAR(60),
	track_id INTEGER,
	rule VARCHAR(80) NOT NULL,
	rule_version VARCHAR(30) NOT NULL,
	calibration_version INTEGER,
	model_version VARCHAR(120) NOT NULL,
	location VARCHAR(150) NOT NULL,
	source_time FLOAT,
	captured_at VARCHAR(40),
	created_at VARCHAR(40),
	explanation TEXT NOT NULL,
	observations JSON NOT NULL,
	raw_ocr JSON NOT NULL,
	plate VARCHAR(25),
	status VARCHAR(30) NOT NULL,
	evidence JSON NOT NULL,
	review_reason TEXT,
	reviewer VARCHAR(60),
	PRIMARY KEY (id),
	UNIQUE (event_key),
	FOREIGN KEY(session_id) REFERENCES tv_sessions (id),
	FOREIGN KEY(camera_id) REFERENCES tv_cameras (id)
)

;

CREATE INDEX IF NOT EXISTS ix_tv_candidates_status ON tv_candidates (status);

CREATE INDEX IF NOT EXISTS ix_tv_candidates_created_at ON tv_candidates (created_at);


CREATE TABLE IF NOT EXISTS tv_jobs (
	id VARCHAR(60) NOT NULL,
	user_id VARCHAR(60) NOT NULL,
	session_id VARCHAR(60) NOT NULL,
	kind VARCHAR(20) NOT NULL,
	status VARCHAR(30) NOT NULL,
	object_key VARCHAR(200),
	upload_token_hash VARCHAR(64),
	upload_expires FLOAT,
	bytes INTEGER,
	seq INTEGER,
	source_ts FLOAT,
	progress FLOAT,
	attempts INTEGER NOT NULL,
	lease_until FLOAT NOT NULL,
	lease_owner VARCHAR(60),
	error VARCHAR(200),
	created_at VARCHAR(40),
	finished_at VARCHAR(40),
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES tv_users (id),
	FOREIGN KEY(session_id) REFERENCES tv_sessions (id)
)

;

CREATE INDEX IF NOT EXISTS ix_tv_jobs_session_id ON tv_jobs (session_id);

CREATE INDEX IF NOT EXISTS ix_tv_jobs_status ON tv_jobs (status);


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


CREATE TABLE IF NOT EXISTS tv_violations (
	id VARCHAR(60) NOT NULL,
	candidate_id VARCHAR(60),
	plate VARCHAR(25),
	rule VARCHAR(80) NOT NULL,
	location VARCHAR(150) NOT NULL,
	created_at VARCHAR(40),
	offense_count INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (candidate_id),
	FOREIGN KEY(candidate_id) REFERENCES tv_candidates (id)
)

;

CREATE INDEX IF NOT EXISTS ix_tv_violations_plate ON tv_violations (plate);


CREATE TABLE IF NOT EXISTS tv_memos (
	id VARCHAR(60) NOT NULL,
	violation_id VARCHAR(60) NOT NULL,
	fine_amount INTEGER NOT NULL,
	status VARCHAR(30) NOT NULL,
	policy_version VARCHAR(30) NOT NULL,
	created_at VARCHAR(40),
	payment_date VARCHAR(40),
	PRIMARY KEY (id),
	CHECK (fine_amount >= 0),
	UNIQUE (violation_id),
	FOREIGN KEY(violation_id) REFERENCES tv_violations (id)
)

;


CREATE TABLE IF NOT EXISTS tv_disputes (
	id VARCHAR(60) NOT NULL,
	memo_id VARCHAR(60) NOT NULL,
	user_id VARCHAR(60) NOT NULL,
	reason TEXT NOT NULL,
	evidence JSON NOT NULL,
	status VARCHAR(30) NOT NULL,
	decision TEXT,
	created_at VARCHAR(40),
	PRIMARY KEY (id),
	UNIQUE (memo_id),
	FOREIGN KEY(memo_id) REFERENCES tv_memos (id),
	FOREIGN KEY(user_id) REFERENCES tv_users (id)
)

;


CREATE TABLE IF NOT EXISTS tv_outbox (
	id VARCHAR(60) NOT NULL,
	memo_id VARCHAR(60) NOT NULL,
	recipient VARCHAR(255) NOT NULL,
	body TEXT NOT NULL,
	status VARCHAR(30) NOT NULL,
	attempts INTEGER NOT NULL,
	next_attempt FLOAT NOT NULL,
	lease_until FLOAT NOT NULL,
	error VARCHAR(150),
	created_at VARCHAR(40),
	PRIMARY KEY (id),
	UNIQUE (memo_id),
	FOREIGN KEY(memo_id) REFERENCES tv_memos (id)
)

;


CREATE TABLE IF NOT EXISTS tv_payments (
	id VARCHAR(60) NOT NULL,
	memo_id VARCHAR(60) NOT NULL,
	user_id VARCHAR(60),
	amount INTEGER NOT NULL,
	mode VARCHAR(30) NOT NULL,
	status VARCHAR(30) NOT NULL,
	created_at VARCHAR(40),
	PRIMARY KEY (id),
	UNIQUE (memo_id),
	FOREIGN KEY(memo_id) REFERENCES tv_memos (id),
	FOREIGN KEY(user_id) REFERENCES tv_users (id)
)

;

COMMIT;
