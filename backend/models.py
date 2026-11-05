"""Versioned application tables. Legacy tables remain untouched by the importer."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import declarative_base
Base = declarative_base()
def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat()

class User(Base):
    __tablename__ = 'tv_users'
    id = Column(String(60), primary_key=True, default=uid)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(10), nullable=False, default='USER')
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(30), default='')
    last_login = Column(String(40))
    token_version = Column(Integer, nullable=False, default=0)
    active = Column(Integer, nullable=False, default=1)
    __table_args__ = (CheckConstraint("role IN ('USER','RTO','GOVT','ADMIN')"),)
class Link(Base):
    __tablename__ = 'tv_ownership'
    id = Column(String(60), primary_key=True, default=uid)
    user_id = Column(String(60), ForeignKey('tv_users.id'), nullable=False)
    plate = Column(String(25), nullable=False, index=True)
    status = Column(String(20), nullable=False, default='PENDING')
    proof = Column(Text, nullable=False, default='')
    reason = Column(Text)
    reviewer = Column(String(60))
    created_at = Column(String(40), default=now)
    __table_args__ = (UniqueConstraint('user_id','plate'),)
class Camera(Base):
    __tablename__ = 'tv_cameras'
    id = Column(String(60), primary_key=True, default=uid)
    name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    source_key = Column(String(100))
    config = Column(JSON, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(String(40), default=now)
class VideoSession(Base):
    __tablename__ = 'tv_sessions'
    id = Column(String(60), primary_key=True, default=uid)
    user_id = Column(String(60), ForeignKey('tv_users.id'), nullable=False)
    camera_id = Column(String(60), ForeignKey('tv_cameras.id'), nullable=False)
    kind = Column(String(20), nullable=False)
    status = Column(String(30), nullable=False, default='RUNNING')
    config = Column(JSON, nullable=False)
    calibration_version = Column(Integer, nullable=False)
    last_seq = Column(Integer, nullable=False, default=-1)
    last_ts = Column(Float, nullable=False, default=-1)
    heartbeat = Column(Float, nullable=False, default=0)
    received = Column(Integer, nullable=False, default=0)
    dropped = Column(Integer, nullable=False, default=0)
    processed = Column(Integer, nullable=False, default=0)
    result = Column(JSON, nullable=False, default=dict)
    preview_key = Column(String(200))
    state = Column(JSON, nullable=False, default=dict)
    created_at = Column(String(40), default=now)
class Job(Base):
    __tablename__ = 'tv_jobs'
    id = Column(String(60), primary_key=True, default=uid)
    user_id = Column(String(60), ForeignKey('tv_users.id'), nullable=False)
    session_id = Column(String(60), ForeignKey('tv_sessions.id'), nullable=False, index=True)
    kind = Column(String(20), nullable=False)
    status = Column(String(30), nullable=False, default='AWAITING_UPLOAD', index=True)
    object_key = Column(String(200))
    upload_token_hash = Column(String(64))
    upload_expires = Column(Float)
    bytes = Column(Integer, default=0)
    seq = Column(Integer)
    source_ts = Column(Float)
    progress = Column(Float, default=0)
    attempts = Column(Integer, nullable=False, default=0)
    lease_until = Column(Float, nullable=False, default=0)
    lease_owner = Column(String(60))
    error = Column(String(200))
    created_at = Column(String(40), default=now)
    finished_at = Column(String(40))
class Candidate(Base):
    __tablename__ = 'tv_candidates'
    id = Column(String(60), primary_key=True, default=uid)
    event_key = Column(String(200), unique=True, nullable=False)
    session_id = Column(String(60), ForeignKey('tv_sessions.id'))
    camera_id = Column(String(60), ForeignKey('tv_cameras.id'))
    track_id = Column(Integer)
    rule = Column(String(80), nullable=False)
    rule_version = Column(String(30), nullable=False, default='movement-1')
    calibration_version = Column(Integer)
    model_version = Column(String(120), nullable=False, default='manual')
    location = Column(String(150), nullable=False)
    source_time = Column(Float)
    captured_at = Column(String(40))
    created_at = Column(String(40), default=now, index=True)
    explanation = Column(Text, nullable=False)
    observations = Column(JSON, nullable=False, default=dict)
    raw_ocr = Column(JSON, nullable=False, default=list)
    plate = Column(String(25))
    status = Column(String(30), nullable=False, default='PENDING', index=True)
    evidence = Column(JSON, nullable=False, default=list)
    review_reason = Column(Text)
    reviewer = Column(String(60))
class Violation(Base):
    __tablename__ = 'tv_violations'
    id = Column(String(60), primary_key=True, default=uid)
    candidate_id = Column(String(60), ForeignKey('tv_candidates.id'), unique=True)
    plate = Column(String(25), index=True)
    rule = Column(String(80), nullable=False)
    location = Column(String(150), nullable=False)
    created_at = Column(String(40), default=now)
    offense_count = Column(Integer, nullable=False, default=1)
class Memo(Base):
    __tablename__ = 'tv_memos'
    id = Column(String(60), primary_key=True, default=uid)
    violation_id = Column(String(60), ForeignKey('tv_violations.id'), unique=True, nullable=False)
    fine_amount = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default='UNPAID')
    policy_version = Column(String(30), nullable=False, default='project-demo-1')
    created_at = Column(String(40), default=now)
    payment_date = Column(String(40))
    __table_args__ = (CheckConstraint('fine_amount >= 0'),)
class Payment(Base):
    __tablename__ = 'tv_payments'
    id = Column(String(60), primary_key=True, default=uid)
    memo_id = Column(String(60), ForeignKey('tv_memos.id'), unique=True, nullable=False)
    user_id = Column(String(60), ForeignKey('tv_users.id'))
    amount = Column(Integer, nullable=False)
    mode = Column(String(30), nullable=False, default='SANDBOX')
    status = Column(String(30), nullable=False, default='SANDBOX_COMPLETED')
    created_at = Column(String(40), default=now)
class Dispute(Base):
    __tablename__ = 'tv_disputes'
    id = Column(String(60), primary_key=True, default=uid)
    memo_id = Column(String(60), ForeignKey('tv_memos.id'), nullable=False, unique=True)
    user_id = Column(String(60), ForeignKey('tv_users.id'), nullable=False)
    reason = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=list)
    status = Column(String(30), nullable=False, default='PENDING')
    decision = Column(Text)
    created_at = Column(String(40), default=now)
class Audit(Base):
    __tablename__ = 'tv_audit'
    id = Column(String(60), primary_key=True, default=uid)
    actor = Column(String(60), nullable=False)
    action = Column(String(100), nullable=False)
    target = Column(String(100), nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(String(40), default=now)
class Outbox(Base):
    __tablename__ = 'tv_outbox'
    id = Column(String(60), primary_key=True, default=uid)
    memo_id = Column(String(60), ForeignKey('tv_memos.id'), nullable=False, unique=True)
    recipient = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default='PREVIEW')
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt = Column(Float, nullable=False, default=0)
    lease_until = Column(Float, nullable=False, default=0)
    error = Column(String(150))
    created_at = Column(String(40), default=now)
class Service(Base):
    __tablename__ = 'tv_services'
    id = Column(String(60), primary_key=True)
    heartbeat = Column(Float, nullable=False)
    details = Column(JSON, nullable=False, default=dict)
class Revocation(Base):
    __tablename__ = 'tv_revocations'
    id = Column(String(60), primary_key=True)
    expires = Column(Float, nullable=False)
class RateLimit(Base):
    __tablename__ = 'tv_rate_limits'
    id = Column(String(100), primary_key=True)
    count = Column(Integer, nullable=False, default=0)
    window = Column(Float, nullable=False)
class Device(Base):
    __tablename__ = 'tv_devices'
    id = Column(String(60), primary_key=True, default=uid)
    camera_id = Column(String(60), ForeignKey('tv_cameras.id'), nullable=False)
    token_hash = Column(String(64), nullable=False)
    active = Column(Integer, nullable=False, default=1)
class Setting(Base):
    __tablename__ = 'tv_settings'
    id = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)

class VehicleProfile(Base):
    __tablename__ = 'tv_vehicle_profiles'
    id = Column(String(25), primary_key=True)  # Normalized plate; ownership still comes from verified links.
    model = Column(String(120), nullable=False, default='')
    vehicle_class = Column(String(30), nullable=False, default='car')
    color = Column(String(40), nullable=False, default='')
    registration_reference = Column(String(100), nullable=False, default='')
    owner_display_name = Column(String(150), nullable=False, default='')
    contact_phone = Column(String(30), nullable=False, default='')
    address = Column(String(300), nullable=False, default='')
    is_demo = Column(Integer, nullable=False, default=0)
    created_at = Column(String(40), default=now)

class DatasetAsset(Base):
    __tablename__ = 'tv_dataset_assets'
    id = Column(String(100), primary_key=True)
    title = Column(String(180), nullable=False)
    category = Column(String(80), nullable=False)
    source_url = Column(Text, nullable=False)
    license = Column(String(100), nullable=False)
    attribution = Column(Text, nullable=False)
    object_key = Column(String(240), nullable=False)
    sha256 = Column(String(64), nullable=False)
    annotations = Column(JSON, nullable=False, default=dict)
    created_at = Column(String(40), default=now)

class CaseMetadata(Base):
    __tablename__ = 'tv_case_metadata'
    id = Column(String(60), ForeignKey('tv_candidates.id'), primary_key=True)
    is_demo = Column(Integer, nullable=False, default=0, index=True)
    asset_id = Column(String(100), ForeignKey('tv_dataset_assets.id'))
    note = Column(Text, nullable=False, default='')
