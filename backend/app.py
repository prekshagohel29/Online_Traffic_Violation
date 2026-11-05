"""Authenticated e-Memo application. All sensitive traffic data goes through this API."""

import os, re, time, secrets, hashlib, math, csv, io
from pathlib import Path
from datetime import timedelta, datetime, timezone
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify, g, abort, Response, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    get_jwt,
    get_jwt_identity,
    create_access_token,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from sqlalchemy import select, func, text, or_, delete
from sqlalchemy.exc import IntegrityError
from .db import make_engine, initialize, transaction
from .models import *
from .storage import Storage
from .rules import validate_config, capability, number
from .camera_sources import validate_sources

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
BASE_FINES = {
    "wrong_way": 500,
    "restricted_zone": 500,
    "red_light": 500,
    "speeding": 1000,
    "no_parking": 200,
    "stop_line": 500,
    "Helmet Violation": 100,
    "Signal Jump": 500,
    "Speeding": 1000,
    "Parking Violation": 200,
    "No License": 2000,
    "Overloading": 1500,
    "Drunk Driving": 5000,
}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def plate(value, required=True):
    if not isinstance(value, str):
        abort(400, description="Plate must be text")
    value = re.sub(r"[\s-]", "", value).upper()
    if not value and not required:
        return None
    if not re.fullmatch(r"[A-Z0-9]{4,20}", value):
        abort(400, description="Plate must contain 4–20 letters or digits")
    return value


def json_body():
    if not request.is_json:
        abort(415, description="JSON content type required")
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400, description="JSON object required")
    return data


def string(data, key, limit=200, required=True):
    val = data.get(key, "")
    if not isinstance(val, str) or len(val) > limit or (required and not val.strip()):
        abort(400, description=f"Valid {key} required (maximum {limit} characters)")
    return val.strip()


def record(row, exclude=()):
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
        if c.name not in exclude
    }


def audit(db, action, target, details=None, actor=None):
    db.add(
        Audit(
            actor=actor or g.user.id,
            action=action,
            target=str(target),
            details=details or {},
        )
    )


def fetch(db, model, ident, lock=False):
    query = select(model).where(model.id == str(ident))
    if lock:
        query = query.with_for_update()
    obj = db.scalar(query)
    if not obj:
        abort(404, description="Record not found")
    return obj


def role(*roles):
    def decorate(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*a, **kw):
            claims = get_jwt()
            with transaction(g.engine) as db:
                user = db.get(User, get_jwt_identity())
                if (
                    not user
                    or not user.active
                    or user.token_version != claims.get("version")
                    or db.get(Revocation, claims["jti"])
                ):
                    abort(401, description="Session expired")
                if roles and user.role not in roles:
                    abort(403, description="This action requires a different role")
                g.user = user
            return fn(*a, **kw)

        return wrapped

    return decorate


def page_query(query):
    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(100, max(1, int(request.args.get("size", 25))))
    except ValueError:
        abort(400, description="Invalid pagination")
    return query.offset((page - 1) * size).limit(size), page, size


def page_result(db, query, mapper=record):
    q, page, size = page_query(query)
    return {
        "items": [mapper(x) for x in db.scalars(q)],
        "page": page,
        "size": size,
        "total": db.scalar(
            select(func.count()).select_from(query.order_by(None).subquery())
        ),
    }


def owner(db, plate_number):
    return bool(
        plate_number
        and db.scalar(
            select(Link.id).where(
                Link.user_id == g.user.id,
                Link.plate == plate_number,
                Link.status == "APPROVED",
            )
        )
    )


def memo_for(db, ident, lock=False):
    memo = fetch(db, Memo, ident, lock)
    violation = fetch(db, Violation, memo.violation_id)
    if g.user.role not in ("ADMIN", "RTO") and not owner(db, violation.plate):
        abort(404, description="Memo not found")
    return memo, violation


def candidate_access(db, c):
    if g.user.role in ("ADMIN", "RTO"):
        return
    violation = db.scalar(select(Violation).where(Violation.candidate_id == c.id))
    if not violation or not owner(db, violation.plate):
        abort(404, description="Evidence not found")


def create_app(overrides=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        DATA_DIR=os.getenv("DATA_DIR", str(ROOT / "data")),
        DATABASE_URL=os.getenv("DATABASE_URL", ""),
        APP_ENV=os.getenv("APP_ENV", "local"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", ""),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=30),
        JWT_ENCODE_ISSUER="e-memo",
        JWT_DECODE_ISSUER="e-memo",
        STORAGE_MODE=os.getenv("STORAGE_MODE", "local"),
        SUPABASE_URL=os.getenv("SUPABASE_URL", ""),
        SUPABASE_SERVICE_ROLE_KEY=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        STORAGE_BUCKET=os.getenv("STORAGE_BUCKET", "traffic-private"),
        MAX_UPLOAD_BYTES=int(os.getenv("MAX_UPLOAD_BYTES", 104857600)),
        MAX_CONTENT_LENGTH=104857600,
        MAX_LOCAL_STORAGE_BYTES=int(os.getenv("MAX_LOCAL_STORAGE_BYTES", 5368709120)),
        FRONTEND_URL=os.getenv("FRONTEND_URL", "http://localhost:3000"),
        CORS_ORIGINS=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        NOTIFICATION_MODE=os.getenv("NOTIFICATION_MODE", "preview"),
        ENABLE_DEMO_FEATURES=os.getenv("ENABLE_DEMO_FEATURES", "0") == "1",
        MODEL_PATH=os.getenv("MODEL_PATH", str(ROOT / "models" / "yolox.onnx")),
        CAMERA_SOURCES=os.getenv("CAMERA_SOURCES", "{}"),
    )
    if overrides:
        app.config.update(overrides)
    validate_sources(app.config["CAMERA_SOURCES"])
    data = Path(app.config["DATA_DIR"])
    data.mkdir(parents=True, exist_ok=True)
    if not app.config["JWT_SECRET_KEY"] or len(app.config["JWT_SECRET_KEY"]) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be configured with at least 32 random characters. Run scripts/setup.ps1 for local use."
        )
    if app.config["APP_ENV"] == "production":
        if (
            not app.config["SUPABASE_URL"].startswith("https://")
            or os.getenv("DB_SSLMODE", "require") == "disable"
        ):
            raise RuntimeError("Production storage and database require TLS")
        if app.config["STORAGE_MODE"] != "supabase" or not all(
            app.config[x]
            for x in ("DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
        ):
            raise RuntimeError(
                "Production requires PostgreSQL and private Supabase storage"
            )
        if not app.config["DATABASE_URL"].startswith(("postgres", "postgresql")):
            raise RuntimeError("Production requires PostgreSQL")
        if not app.config["FRONTEND_URL"].startswith("https://") or any(
            not x.startswith("https://") or "*" in x for x in app.config["CORS_ORIGINS"]
        ):
            raise RuntimeError("Exact HTTPS frontend origins required")
    url = app.config["DATABASE_URL"] or f'sqlite:///{(data/"traffic.db").as_posix()}'
    engine = make_engine(url)
    app.extensions["engine"] = engine
    app.extensions["storage"] = Storage(app.config)
    JWTManager(app)
    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-Sequence",
            "X-Source-Time",
            "X-Device-Token",
            "X-Signal-State",
            "X-Signal-Time",
        ],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    @app.before_request
    def context():
        g.engine = engine
        g.storage = app.extensions["storage"]
        if (
            request.is_json
            and request.content_length
            and request.content_length > 65536
        ):
            abort(413, description="JSON body exceeds 64 KiB")

    @app.after_request
    def headers(resp):
        resp.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store",
                "Permissions-Policy": "camera=(self)",
            }
        )
        return resp

    @app.errorhandler(Exception)
    def errors(exc):
        if isinstance(exc, HTTPException):
            return jsonify(msg=exc.description), exc.code
        if isinstance(exc, (ValueError, TypeError)):
            return jsonify(msg=str(exc)[:200]), 400
        if isinstance(exc, IntegrityError):
            return (
                jsonify(
                    msg="This record already exists or conflicts with another action"
                ),
                409,
            )
        app.logger.error("Request failed: %s", type(exc).__name__)
        return (
            jsonify(
                msg="Service could not complete the request; retry or contact the operator"
            ),
            503,
        )

    def throttle(key, limit=20, window=60):
        # Database-backed limit works across API processes. Do not trust spoofed forwarding headers.
        key = digest(key)
        with transaction(engine) as db:
            if engine.dialect.name == "postgresql":
                db.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key}
                )
            row = db.get(RateLimit, key)
            if not row:
                row = RateLimit(id=key, count=0, window=time.time())
                db.add(row)
            if time.time() - row.window > window:
                row.count = 0
                row.window = time.time()
            if row.count >= limit:
                abort(429, description="Rate limit reached; wait and retry")
            row.count += 1

    def issue(user):
        return jsonify(
            access_token=create_access_token(
                identity=user.id, additional_claims={"version": user.token_version}
            ),
            user=record(user, ("password_hash", "token_version", "active")),
        )

    @app.post("/api/auth/register")
    def register():
        throttle("register:" + str(request.remote_addr), 10, 3600)
        d = json_body()
        if d.get("role", "USER") != "USER":
            abort(403, description="Public signup can create citizen accounts only")
        email = string(d, "email", 255).lower()
        password = string(d, "password", 200)
        name = string(d, "full_name", 150)
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(password) < 10:
            abort(
                400,
                description="Valid email and password of at least 10 characters required",
            )
        with transaction(engine) as db:
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                role="USER",
                full_name=name,
                phone_number=string(d, "phone_number", 30, False),
            )
            db.add(user)
            db.flush()
            if d.get("vehicle_number"):
                db.add(
                    Link(
                        user_id=user.id,
                        plate=plate(d["vehicle_number"]),
                        proof="Signup request — ownership proof must be supplied before approval",
                    )
                )
            audit(db, "REGISTER", user.id, actor=user.id)
        return issue(user)

    @app.post("/api/auth/login")
    def login():
        d = json_body()
        throttle("login:" + str(request.remote_addr), 30, 300)
        email = string(d, "email", 255).lower()
        password = string(d, "password", 200)
        with transaction(engine) as db:
            user = db.scalar(select(User).where(User.email == email))
            valid = (
                check_password_hash(user.password_hash, password)
                if user
                else check_password_hash(
                    generate_password_hash("unused-dummy-password"), password
                )
            )
            if not user or not valid or not user.active:
                abort(401, description="Email or password is incorrect")
            user.last_login = now()
        return issue(user)

    @app.get("/api/auth/me")
    @role()
    def me():
        return jsonify(record(g.user, ("password_hash", "token_version", "active")))

    @app.post("/api/auth/logout")
    @role()
    def logout():
        with transaction(engine) as db:
            db.merge(Revocation(id=get_jwt()["jti"], expires=get_jwt()["exp"]))
        return jsonify(msg="Signed out")

    @app.put("/api/user/profile")
    @role()
    def profile():
        d = json_body()
        with transaction(engine) as db:
            u = fetch(db, User, g.user.id, True)
            u.full_name = string(d, "full_name", 150)
            u.phone_number = string(d, "phone_number", 30, False)
            if d.get("password"):
                if not check_password_hash(
                    u.password_hash, string(d, "current_password", 200)
                ):
                    abort(403, description="Current password required")
                password = string(d, "password", 200)
                if len(password) < 10:
                    abort(
                        400, description="New password must have at least 10 characters"
                    )
                u.password_hash = generate_password_hash(password)
                u.token_version += 1
            audit(db, "UPDATE_PROFILE", u.id)
        return jsonify(
            msg="Profile updated. Sign in again if you changed your password."
        )

    @app.get("/api/user/vehicles")
    @role("USER", "RTO", "ADMIN")
    def vehicles():
        with transaction(engine) as db:
            result = []
            for x in db.scalars(select(Link).where(Link.user_id == g.user.id)):
                item = record(x)
                profile = (
                    db.get(VehicleProfile, x.plate) if x.status == "APPROVED" else None
                )
                item["vehicle_model"] = profile.model if profile else None
                result.append(item)
            return jsonify(result)

    @app.post("/api/user/vehicles/link")
    @role("USER")
    def link_vehicle():
        d = json_body()
        with transaction(engine) as db:
            link = Link(
                user_id=g.user.id,
                plate=plate(d.get("plate", "")),
                proof=string(d, "proof", 2000),
            )
            db.add(link)
            db.flush()
            audit(db, "REQUEST_OWNERSHIP", link.id)
        return (
            jsonify(msg="Ownership request pending RTO verification", id=link.id),
            201,
        )

    @app.get("/api/operator/ownership")
    @role("ADMIN", "RTO")
    def ownership():
        with transaction(engine) as db:

            def mapped(x):
                return {**record(x), "applicant": fetch(db, User, x.user_id).email}

            return jsonify(
                page_result(db, select(Link).order_by(Link.created_at.desc()), mapped)
            )

    @app.post("/api/operator/ownership/<ident>/review")
    @role("ADMIN", "RTO")
    def review_ownership(ident):
        d = json_body()
        decision = d.get("decision")
        reason = string(d, "reason", 2000)
        if decision not in ("APPROVED", "REJECTED"):
            abort(400, description="Invalid decision")
        with transaction(engine) as db:
            link = fetch(db, Link, ident, True)
            if link.status != "PENDING":
                abort(409, description="Ownership request already reviewed")
            if decision == "APPROVED" and (
                not d.get("proof_checked") or link.proof.startswith("Signup request")
            ):
                abort(
                    400,
                    description="Verify ownership documentation; signup plate alone is insufficient",
                )
            if decision == "APPROVED":
                if engine.dialect.name == "postgresql":
                    db.execute(
                        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                        {"key": link.plate},
                    )
                if db.scalar(
                    select(Link.id).where(
                        Link.plate == link.plate, Link.status == "APPROVED"
                    )
                ):
                    abort(
                        409,
                        description="Vehicle already has verified ownership; use a documented transfer process",
                    )
            link.status = decision
            link.reason = reason
            link.reviewer = g.user.id
            audit(db, "OWNERSHIP_" + decision, link.id, {"reason": reason})
        return jsonify(msg="Ownership decision recorded")

    def memo_data(db, m):
        v = fetch(db, Violation, m.violation_id)
        c = db.get(Candidate, v.candidate_id) if v.candidate_id else None
        payment = db.scalar(select(Payment).where(Payment.memo_id == m.id))
        dispute = db.scalar(select(Dispute).where(Dispute.memo_id == m.id))
        return {
            **record(m),
            "memo_id": m.id,
            "plate": v.plate,
            "violation_type": v.rule,
            "location": v.location,
            "date_time": v.created_at,
            "source_time": c.source_time if c else None,
            "candidate_id": v.candidate_id,
            "offense_count": v.offense_count,
            "payment": record(payment) if payment else None,
            "dispute": record(dispute) if dispute else None,
            "policy_label": "Project demonstration policy — not an official challan",
        }

    @app.get("/api/user/memos")
    @role("USER")
    def user_memos():
        with transaction(engine) as db:
            q = (
                select(Memo)
                .join(Violation)
                .where(
                    Violation.plate.in_(
                        select(Link.plate).where(
                            Link.user_id == g.user.id, Link.status == "APPROVED"
                        )
                    )
                )
            )
            if request.args.get("vehicle_number"):
                q = q.where(Violation.plate == request.args["vehicle_number"])
            if request.args.get("status") and request.args["status"] != "ALL":
                q = q.where(Memo.status == request.args["status"])
            if request.args.get("q"):
                q = q.where(
                    or_(
                        Violation.plate.contains(request.args["q"][:100]),
                        Violation.rule.contains(request.args["q"][:100]),
                    )
                )
            return jsonify(
                page_result(
                    db, q.order_by(Memo.created_at.desc()), lambda m: memo_data(db, m)
                )
            )

    @app.get("/fines")
    @app.get("/api/operator/memos")
    @role("ADMIN", "RTO")
    def memos():
        with transaction(engine) as db:
            return jsonify(
                page_result(
                    db,
                    select(Memo).order_by(Memo.created_at.desc()),
                    lambda m: memo_data(db, m),
                )
            )

    @app.post("/api/user/pay")
    @role("USER")
    def pay():
        d = json_body()
        if d.get("mode") != "SANDBOX" or d.get("acknowledge_no_money") is not True:
            abort(
                400,
                description="Explicit sandbox acknowledgement required; no real money is transferred",
            )
        with transaction(engine) as db:
            m, v = memo_for(db, d.get("memo_id"), True)
            existing = db.scalar(select(Payment).where(Payment.memo_id == m.id))
            if existing:
                return jsonify(record(existing))
            if m.status != "UNPAID":
                abort(
                    409,
                    description="Only undisputed unpaid memos can be paid in sandbox",
                )
            p = Payment(memo_id=m.id, user_id=g.user.id, amount=m.fine_amount)
            db.add(p)
            db.flush()
            m.status = "SANDBOX_PAID"
            m.payment_date = now()
            audit(db, "SANDBOX_PAYMENT", m.id, {"receipt": p.id, "amount": p.amount})
        return jsonify(record(p)), 201

    @app.post("/api/user/disputes")
    @role("USER")
    def dispute():
        d = json_body()
        with transaction(engine) as db:
            m, v = memo_for(db, d.get("memo_id"), True)
            if m.status != "UNPAID":
                abort(
                    409,
                    description="Only unpaid memos can be disputed. Paid cases require administrator reconciliation.",
                )
            row = Dispute(
                memo_id=m.id, user_id=g.user.id, reason=string(d, "reason", 3000)
            )
            db.add(row)
            db.flush()
            m.status = "DISPUTED"
            audit(db, "OPEN_DISPUTE", row.id)
        return jsonify(record(row)), 201

    @app.get("/api/operator/disputes")
    @role("ADMIN", "RTO")
    def disputes():
        with transaction(engine) as db:
            return jsonify(
                page_result(db, select(Dispute).order_by(Dispute.created_at.desc()))
            )

    @app.post("/api/disputes/<ident>/evidence")
    @role("USER")
    def attach_dispute_evidence(ident):
        if request.content_type not in ("image/jpeg", "image/png"):
            abort(415, description="JPEG or PNG evidence required")
        data = request.get_data()
        if not 100 <= len(data) <= 2 * 1024 * 1024:
            abort(413, description="Evidence must be under 2 MiB")
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        if max(image.size) > 4096:
            abort(400, description="Image exceeds 4096px")
        image = image.convert("RGB")
        encoded = io.BytesIO()
        image.save(encoded, format="JPEG", quality=85)
        with transaction(engine) as db:
            d = fetch(db, Dispute, ident, True)
            memo_for(db, d.memo_id)
            if d.user_id != g.user.id:
                abort(404)
            if d.status != "PENDING" or len(d.evidence) >= 4:
                abort(
                    409, description="Evidence limit reached or dispute already decided"
                )
            evidence = g.storage.put(f"disputes/{d.id}/{uid()}.jpg", encoded.getvalue())
            d.evidence = [*d.evidence, evidence]
            audit(db, "ATTACH_DISPUTE_EVIDENCE", d.id, {"sha256": evidence["sha256"]})
        return jsonify(msg="Supporting evidence saved"), 201

    @app.get("/api/disputes/<ident>/evidence/<int:index>")
    @role("ADMIN", "RTO", "USER")
    def dispute_evidence(ident, index):
        with transaction(engine) as db:
            d = fetch(db, Dispute, ident)
            memo_for(db, d.memo_id)
            if g.user.role == "USER" and d.user_id != g.user.id:
                abort(404)
            if index < 0 or index >= len(d.evidence):
                abort(404)
            evidence = d.evidence[index]
        data = g.storage.get(evidence["key"])
        if hashlib.sha256(data).hexdigest() != evidence["sha256"]:
            abort(409, description="Evidence integrity check failed")
        return Response(data, mimetype="image/jpeg")

    @app.post("/api/operator/disputes/<ident>/review")
    @role("ADMIN", "RTO")
    def decide_dispute(ident):
        d = json_body()
        decision = d.get("decision")
        if decision not in ("UPHELD", "DISMISSED"):
            abort(400, description="Choose UPHELD or DISMISSED")
        with transaction(engine) as db:
            row = fetch(db, Dispute, ident, True)
            if row.status != "PENDING":
                abort(409, description="Dispute already decided")
            m = fetch(db, Memo, row.memo_id, True)
            if m.status != "DISPUTED":
                abort(409, description="Memo changed; reload before deciding")
            row.status = decision
            row.decision = string(d, "reason", 3000)
            m.status = "VOID" if decision == "UPHELD" else "UNPAID"
            audit(db, "DISPUTE_" + decision, row.id, {"reason": row.decision})
        return jsonify(msg="Dispute decision recorded")

    @app.get("/api/operator/candidates")
    @role("ADMIN", "RTO")
    def candidates():
        with transaction(engine) as db:
            q = select(Candidate)
            if request.args.get("status"):
                q = q.where(Candidate.status == request.args["status"])
            if request.args.get("session_id"):
                q = q.where(Candidate.session_id == request.args["session_id"])
            return jsonify(page_result(db, q.order_by(Candidate.created_at.desc())))

    @app.get("/api/candidates/<ident>")
    @role("ADMIN", "RTO", "USER")
    def candidate_detail(ident):
        with transaction(engine) as db:
            c = fetch(db, Candidate, ident)
            candidate_access(db, c)
            data = record(c)
            if g.user.role == "USER":
                data.pop("reviewer", None)
            data["history"] = (
                [
                    record(x)
                    for x in db.scalars(
                        select(Audit)
                        .where(Audit.target == c.id)
                        .order_by(Audit.created_at)
                    )
                ]
                if g.user.role != "USER"
                else []
            )
            data["related_candidates"] = (
                [
                    {
                        "id": x.id,
                        "status": x.status,
                        "source_time": x.source_time,
                        "session_id": x.session_id,
                    }
                    for x in db.scalars(
                        select(Candidate)
                        .where(
                            Candidate.camera_id == c.camera_id,
                            Candidate.rule == c.rule,
                            Candidate.id != c.id,
                        )
                        .order_by(Candidate.created_at.desc())
                        .limit(5)
                    )
                ]
                if g.user.role != "USER"
                else []
            )
            return jsonify(data)

    @app.post("/addViolation")
    @app.post("/api/operator/manual")
    @role("ADMIN", "RTO")
    def manual():
        d = json_body()
        key = request.headers.get("Idempotency-Key", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", key):
            abort(
                400, description="An idempotency key of 8–80 letters/digits is required"
            )
        rule_name = string(d, "type", 80)
        if rule_name not in BASE_FINES:
            abort(400, description="Unsupported manual violation type")
        with transaction(engine) as db:
            event = "manual:" + g.user.id + ":" + key
            existing = db.scalar(select(Candidate).where(Candidate.event_key == event))
            if existing:
                return jsonify(record(existing))
            c = Candidate(
                event_key=event,
                rule=rule_name,
                plate=plate(d.get("plate", ""), False),
                location=string(d, "location", 150),
                explanation=string(d, "explanation", 3000),
                observations={
                    "source": "manual",
                    "submitted_by": g.user.id,
                    "evidence_status": "Awaiting operator attachment",
                },
            )
            db.add(c)
            db.flush()
            audit(db, "SUBMIT_MANUAL_CANDIDATE", c.id)
        return jsonify(record(c)), 201

    @app.post("/api/admin/verify")
    @app.post("/api/operator/candidates/<ident>/review")
    @role("ADMIN", "RTO")
    def review(ident=None):
        d = json_body()
        ident = ident or d.get("candidate_id")
        decision = d.get("decision")
        reason = string(d, "reason", 3000)
        if decision not in ("CONFIRMED", "REJECTED", "NEEDS_EVIDENCE"):
            abort(400, description="Invalid review decision")
        with transaction(engine) as db:
            c = fetch(db, Candidate, ident, True)
            if c.status in ("CONFIRMED", "REJECTED"):
                if c.status == decision:
                    return jsonify(msg="Decision already recorded", candidate_id=c.id)
                abort(409, description="Candidate already finalized")
            corrected = plate(d.get("plate", c.plate or ""), False)
            if decision == "CONFIRMED":
                if not c.evidence:
                    abort(409, description="Attach evidence before confirming")
                if not d.get("evidence_reviewed"):
                    abort(400, description="Evidence review acknowledgement required")
                if corrected and engine.dialect.name == "postgresql":
                    db.execute(
                        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                        {"key": corrected + ":" + c.rule},
                    )
                count = 1
                if corrected:
                    count += db.scalar(
                        select(func.count())
                        .select_from(Violation)
                        .join(Memo)
                        .where(
                            Violation.plate == corrected,
                            Violation.rule == c.rule,
                            Memo.status != "VOID",
                        )
                    )
                v = Violation(
                    candidate_id=c.id,
                    plate=corrected,
                    rule=c.rule,
                    location=c.location,
                    offense_count=count,
                )
                db.add(v)
                db.flush()
                policy = db.get(Setting, "fine_policy")
                config = (
                    policy.value
                    if policy
                    else {"version": "project-demo-1", "bases": BASE_FINES}
                )
                fine = int(config["bases"].get(c.rule, 500)) * count * count
                if d.get("fine_amount") is not None:
                    fine = int(number(d["fine_amount"], 0, 1000000, "Fine override"))
                    string(d, "override_reason", 1000)
                m = Memo(
                    violation_id=v.id,
                    fine_amount=min(fine, 1000000),
                    policy_version=config["version"],
                )
                db.add(m)
                db.flush()
                verified = (
                    db.scalar(
                        select(User)
                        .join(Link, Link.user_id == User.id)
                        .where(Link.plate == corrected, Link.status == "APPROVED")
                    )
                    if corrected
                    else None
                )
                if verified:
                    url = app.config["FRONTEND_URL"].rstrip("/") + "/dashboard"
                    db.add(
                        Outbox(
                            memo_id=m.id,
                            recipient=verified.email,
                            body=f"PROJECT DEMONSTRATION MEMO {m.id}\nVehicle: {corrected}\nType: {c.rule}\nAmount: INR {m.fine_amount}\nReview at {url}\nNot an official government challan.",
                            status=(
                                "QUEUED"
                                if app.config["NOTIFICATION_MODE"] == "smtp"
                                else "PREVIEW"
                            ),
                        )
                    )
                audit(
                    db,
                    "ISSUE_PROJECT_MEMO",
                    m.id,
                    {
                        "candidate": c.id,
                        "policy": config["version"],
                        "override_reason": d.get("override_reason"),
                        "owner_dispatch": bool(verified),
                    },
                )
            c.status = decision
            c.plate = corrected
            c.review_reason = reason
            c.reviewer = g.user.id
            audit(
                db,
                "REVIEW_" + decision,
                c.id,
                {
                    "reason": reason,
                    "corrected_plate": corrected,
                    "original_plate": c.observations.get("original_plate"),
                },
            )
        return jsonify(msg="Review decision persisted", candidate_id=c.id)

    @app.post("/api/candidates/<ident>/evidence")
    @role("ADMIN", "RTO")
    def attach_evidence(ident):
        if request.content_type not in ("image/jpeg", "image/png"):
            abort(415, description="JPEG or PNG evidence required")
        data = request.get_data()
        if not 100 <= len(data) <= 2 * 1024 * 1024:
            abort(413, description="Evidence must be under 2 MiB")
        import cv2, numpy as np

        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if image is None or max(image.shape[:2]) > 4096:
            abort(400, description="Invalid evidence image")
        with transaction(engine) as db:
            c = fetch(db, Candidate, ident, True)
            if c.status not in ("PENDING", "NEEDS_EVIDENCE"):
                abort(409, description="Candidate is finalized")
            if len(c.evidence) >= 8:
                abort(409, description="Evidence limit reached")
            _, encoded = cv2.imencode(".jpg", image)
            evidence = g.storage.put(f"evidence/{c.id}/{uid()}.jpg", encoded.tobytes())
            c.evidence = [*c.evidence, evidence]
            audit(db, "ATTACH_EVIDENCE", c.id, {"sha256": evidence["sha256"]})
        return jsonify(msg="Evidence attached"), 201

    @app.get("/api/candidates/<ident>/evidence/<int:index>")
    @role("ADMIN", "RTO", "USER")
    def evidence(ident, index):
        with transaction(engine) as db:
            c = fetch(db, Candidate, ident)
            candidate_access(db, c)
            if index < 0 or index >= len(c.evidence):
                abort(404, description="Evidence missing")
            item = c.evidence[index]
        try:
            data = g.storage.get(item["key"])
        except (FileNotFoundError, KeyError):
            abort(404, description="Evidence missing or expired under retention policy")
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            abort(409, description="Evidence integrity check failed")
        return Response(data, mimetype=item.get("content_type", "image/jpeg"))

    @app.get("/api/memos/<ident>/pdf")
    @role("ADMIN", "RTO", "USER")
    def memo_pdf(ident):
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.utils import simpleSplit

        with transaction(engine) as db:
            m, v = memo_for(db, ident)
            c = db.get(Candidate, v.candidate_id) if v.candidate_id else None
            payment = db.scalar(select(Payment).where(Payment.memo_id == m.id))
            lines = [
                "e-Memo | Project demonstration",
                "NOT AN OFFICIAL GOVERNMENT CHALLAN",
                f"Reference: {m.id}",
                f'Vehicle: {v.plate or "Unreadable / unknown"}',
                f"Violation: {v.rule}",
                f"Location: {v.location}",
                f"Recorded (UTC): {v.created_at}",
                f"Amount: INR {m.fine_amount}",
                f"Status: {m.status}",
                f"Policy: {m.policy_version} (quadratic project/demo policy)",
                f'Source timeline: {c.source_time if c else "unavailable"} seconds',
                f"Evidence: {len(c.evidence) if c else 0} item(s)",
                f'Receipt: {payment.id if payment else "No payment recorded"}',
                "SANDBOX receipts do not represent financial settlement.",
                "No licence is automatically cancelled.",
            ]
            if c:
                lines.append(app.config["FRONTEND_URL"].rstrip("/") + "/cases/" + c.id)
        buffer = io.BytesIO()
        pdf = Canvas(buffer)
        y = 800
        for line in lines:
            for part in simpleSplit(line, "Helvetica", 10, 480):
                pdf.drawString(50, y, part)
                y -= 18
        pdf.save()
        return Response(
            buffer.getvalue(),
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="project-memo-{m.id}.pdf"'
            },
        )

    register_video_routes(app, engine)
    register_admin_routes(app, engine, throttle)
    from .experience import register_experience

    register_experience(app, engine)
    return app


def register_video_routes(app, engine):
    import json

    def session_for(db, ident, lock=False):
        row = fetch(db, VideoSession, ident, lock)
        if row.user_id != g.user.id and g.user.role != "ADMIN":
            abort(404, description="Session not found")
        return row

    def start_session(db, d, kind):
        camera = fetch(db, Camera, d.get("camera_id"))
        if (
            db.scalar(
                select(func.count())
                .select_from(VideoSession)
                .where(VideoSession.status == "RUNNING", VideoSession.kind != "upload")
            )
            >= 4
        ):
            abort(429, description="Live session limit reached; stop an unused source")
        s = VideoSession(
            user_id=g.user.id,
            camera_id=camera.id,
            kind=kind,
            config=camera.config,
            calibration_version=camera.version,
            heartbeat=time.time(),
        )
        db.add(s)
        db.flush()
        return s

    def model_health(db):
        services = list(
            db.scalars(select(Service).where(Service.heartbeat > time.time() - 30))
        )
        return {
            "workers": len(services),
            "model_ready": any(x.details.get("model_ready") for x in services),
            "workers_detail": [record(x) for x in services],
        }

    from .member3_admin import register_member3_health

    register_member3_health(app, engine, model_health)

    @app.get("/health")
    def health():
        return jsonify(status="ok", api="online")

    @app.get("/ready")
    def ready():
        with transaction(engine) as db:
            db.execute(select(1))
            h = model_health(db)
            return jsonify(
                api="online",
                database="online",
                queue="database",
                model="ready" if h["model_ready"] else "unavailable",
                worker="online" if h["workers"] else "offline",
            )

    @app.get("/api/operator/cameras")
    @role("ADMIN", "RTO")
    def cameras():
        with transaction(engine) as db:
            health = model_health(db)
            return jsonify(
                [
                    dict(
                        record(c),
                        capabilities=capability(c.config, health["model_ready"]),
                    )
                    for c in db.scalars(select(Camera).order_by(Camera.created_at))
                ]
            )

    @app.post("/api/operator/cameras")
    @role("ADMIN", "RTO")
    def add_camera():
        d = json_body()
        source = string(d, "source_key", 100, False)
        if source and (
            g.user.role != "ADMIN"
            or source not in json.loads(app.config["CAMERA_SOURCES"])
        ):
            abort(
                400,
                description="A configured source key and administrator role are required for IP cameras",
            )
        with transaction(engine) as db:
            c = Camera(
                name=string(d, "name", 100),
                location=string(d, "location", 150),
                config=validate_config(d.get("config", {})),
                source_key=source or None,
            )
            db.add(c)
            db.flush()
            audit(db, "CREATE_CAMERA", c.id)
        return jsonify(record(c)), 201

    @app.put("/api/operator/cameras/<ident>")
    @role("ADMIN", "RTO")
    def configure(ident):
        d = json_body()
        config = validate_config(d.get("config"))
        with transaction(engine) as db:
            camera = fetch(db, Camera, ident, True)
            if d.get("version") != camera.version:
                abort(
                    409,
                    description="Camera configuration changed; reload before saving",
                )
            camera.config = config
            camera.version += 1
            camera.name = string(d, "name", 100)
            camera.location = string(d, "location", 150)
            # Never silently apply new geometry to an existing session.
            for s in db.scalars(
                select(VideoSession).where(
                    VideoSession.camera_id == ident, VideoSession.status == "RUNNING"
                )
            ):
                s.status = "CALIBRATION_CHANGED"
            audit(
                db,
                "CONFIGURE_CAMERA",
                ident,
                {"version": camera.version, "config": config},
            )
        return jsonify(record(camera))

    @app.post("/api/operator/sessions")
    @role("ADMIN", "RTO")
    def start():
        d = json_body()
        kind = d.get("kind", "webcam")
        if kind not in ("webcam", "ip"):
            abort(400, description="Source must be webcam or configured IP camera")
        with transaction(engine) as db:
            h = model_health(db)
            if not h["model_ready"]:
                abort(
                    503,
                    description="Inference worker or object detector is unavailable. See Model readiness.",
                )
            s = start_session(db, d, kind)
            if kind == "ip":
                c = fetch(db, Camera, s.camera_id)
                if not c.source_key or c.source_key not in json.loads(
                    app.config["CAMERA_SOURCES"]
                ):
                    abort(
                        400,
                        description="Authorized IP camera gateway is not configured",
                    )
                db.add(
                    Job(user_id=g.user.id, session_id=s.id, kind="ip", status="QUEUED")
                )
            audit(db, "START_SESSION", s.id, {"kind": kind})
        return jsonify(record(s)), 201

    @app.get("/api/operator/sessions/<ident>")
    @role("ADMIN", "RTO")
    def session_status(ident):
        with transaction(engine) as db:
            s = session_for(db, ident)
            data = record(s, ("state",))
            data["preview_url"] = (
                f"/api/operator/sessions/{s.id}/preview" if s.preview_key else None
            )
            return jsonify(data)

    @app.get("/api/operator/sessions/<ident>/preview")
    @role("ADMIN", "RTO")
    def preview(ident):
        with transaction(engine) as db:
            s = session_for(db, ident)
            if not s.preview_key:
                abort(404, description="No processed frame yet")
            key = s.preview_key
        try:
            return Response(g.storage.get(key), mimetype="image/jpeg")
        except FileNotFoundError:
            abort(404, description="Preview expired")

    @app.post("/api/operator/sessions/<ident>/stop")
    @role("ADMIN", "RTO")
    def stop(ident):
        with transaction(engine) as db:
            s = session_for(db, ident, True)
            s.status = "STOPPED"
            s.heartbeat = time.time()
            for job in db.scalars(
                select(Job).where(
                    Job.session_id == s.id,
                    Job.status.in_(["QUEUED", "RUNNING", "AWAITING_UPLOAD"]),
                )
            ):
                job.status = "CANCELLED"
            audit(db, "STOP_SESSION", s.id)
        return jsonify(msg="Session stopped")

    @app.post("/api/operator/sessions/<ident>/frames")
    @role("ADMIN", "RTO")
    def frame(ident):
        if request.content_type != "image/jpeg":
            abort(415, description="JPEG frames required")
        data = request.get_data()
        if not 100 <= len(data) <= 512 * 1024:
            abort(413, description="Frame must be under 512 KiB")
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        if max(image.size) > 1280 or min(image.size) < 100:
            abort(
                400,
                description=f"Frame dimensions must be 100–1280 pixels (received {image.width}×{image.height})",
            )
        seq = int(request.headers.get("X-Sequence", "-1"))
        ts = float(request.headers.get("X-Source-Time", "-1"))
        number(seq, 0, 1e9, "Sequence")
        number(ts, 0, 86400, "Source timestamp")
        with transaction(engine) as db:
            s = session_for(db, ident, True)
            if s.kind != "webcam" or s.status != "RUNNING":
                abort(409, description="Session is not accepting webcam frames")
            if seq <= s.last_seq or ts <= s.last_ts:
                abort(409, description="Replayed or stale frame rejected")
            if time.time() - s.heartbeat < 0.45 and s.received:
                abort(429, description="Maximum input rate is 2 FPS")
            for old in db.scalars(
                select(Job).where(
                    Job.session_id == s.id, Job.kind == "frame", Job.status == "QUEUED"
                )
            ):
                old.status = "DROPPED"
                s.dropped += 1
            # One processing frame plus one replaceable queued frame per source.
            jid = uid()
            key = f"frames/{s.id}/{jid}.jpg"
            g.storage.put(key, data)
            signal = None
            if request.headers.get("X-Signal-State"):
                state = request.headers["X-Signal-State"]
                stamp = float(request.headers.get("X-Signal-Time", "-1"))
                if state not in ("red", "green", "unknown"):
                    abort(400, description="Invalid manual signal")
                number(stamp, 0, ts, "Signal timestamp")
                signal = {"state": state, "timestamp": stamp, "source": "MANUAL"}
            result = dict(s.result)
            result["manual_signal"] = signal
            s.result = result
            s.last_seq = seq
            s.last_ts = ts
            s.received += 1
            s.heartbeat = time.time()
            db.add(
                Job(
                    id=jid,
                    user_id=g.user.id,
                    session_id=s.id,
                    kind="frame",
                    status="QUEUED",
                    object_key=key,
                    seq=seq,
                    source_ts=ts,
                )
            )
        return jsonify(accepted=True, sequence=seq), 202

    @app.post("/api/operator/uploads")
    @role("ADMIN", "RTO")
    def upload_ticket():
        d = json_body()
        size = int(
            number(d.get("size", 0), 100, app.config["MAX_UPLOAD_BYTES"], "Video bytes")
        )
        ext = Path(string(d, "filename", 150)).suffix.lower()
        if ext not in (".mp4", ".webm", ".avi", ".mov"):
            abort(400, description="Use MP4, WebM, AVI or MOV video")
        with transaction(engine) as db:
            if (
                db.scalar(
                    select(func.count())
                    .select_from(Job)
                    .where(
                        Job.kind == "upload",
                        Job.status.in_(["AWAITING_UPLOAD", "QUEUED", "RUNNING"]),
                    )
                )
                >= 10
            ):
                abort(429, description="Video job queue is full")
            s = start_session(db, d, "upload")
            jid = uid()
            token = secrets.token_urlsafe(32)
            key = f"uploads/{jid}{ext}"
            expires = 7200 if app.config["STORAGE_MODE"] == "supabase" else 600
            job = Job(
                id=jid,
                user_id=g.user.id,
                session_id=s.id,
                kind="upload",
                object_key=key,
                upload_token_hash=digest(token),
                upload_expires=time.time() + expires,
                bytes=size,
            )
            db.add(job)
            db.flush()
        if app.config["STORAGE_MODE"] == "supabase":
            url = g.storage.signed_upload(key)
            method = "PUT"
            headers = {
                "Content-Type": d.get("content_type", "video/mp4"),
                "x-upsert": "false",
            }
        else:
            url = f"/api/uploads/{jid}?token={token}"
            method = "PUT"
            headers = {"Content-Type": "application/octet-stream"}
        return (
            jsonify(
                job_id=jid,
                session_id=s.id,
                upload_url=url,
                method=method,
                headers=headers,
                expires_in=expires,
                max_bytes=app.config["MAX_UPLOAD_BYTES"],
            ),
            201,
        )

    @app.put("/api/uploads/<ident>")
    def local_upload(ident):
        if app.config["STORAGE_MODE"] != "local":
            abort(404)
        token = request.args.get("token", "")
        with transaction(engine) as db:
            j = fetch(db, Job, ident, True)
            if (
                not j.upload_token_hash
                or not secrets.compare_digest(j.upload_token_hash, digest(token))
                or time.time() > j.upload_expires
            ):
                abort(403, description="Upload authorization expired")
            if j.status != "AWAITING_UPLOAD":
                abort(409, description="Upload ticket already used")
            if request.content_length != j.bytes:
                abort(400, description="Upload size does not match authorization")
            j.status = "UPLOADING"
            key = j.object_key
            expected = j.bytes
        path = g.storage.path(key)
        total = 0
        g.storage.capacity(expected)
        try:
            with path.open("wb") as f:
                while chunk := request.stream.read(1024 * 1024):
                    total += len(chunk)
                    if total > expected:
                        abort(413)
                    f.write(chunk)
            if total != expected:
                abort(400, description="Incomplete upload")
            with transaction(engine) as db:
                fetch(db, Job, ident, True).status = "UPLOADED"
        except Exception:
            path.unlink(missing_ok=True)
            with transaction(engine) as db:
                fetch(db, Job, ident, True).status = "AWAITING_UPLOAD"
            raise
        return jsonify(msg="Upload complete")

    @app.post("/api/operator/jobs/<ident>/submit")
    @role("ADMIN", "RTO")
    def submit_job(ident):
        with transaction(engine) as db:
            j = fetch(db, Job, ident, True)
            session_for(db, j.session_id)
            if j.status not in ("AWAITING_UPLOAD", "UPLOADED"):
                abort(409, description="Job already submitted or cancelled")
            if app.config["STORAGE_MODE"] == "local" and j.status != "UPLOADED":
                abort(409, description="Upload video first")
            j.status = "QUEUED"
            j.upload_token_hash = None
            audit(db, "SUBMIT_VIDEO", j.id)
        return jsonify(msg="Video queued"), 202

    @app.get("/api/operator/jobs")
    @role("ADMIN", "RTO")
    def jobs():
        with transaction(engine) as db:
            q = select(Job).where(Job.kind.in_(["upload", "ip"]))
            if g.user.role != "ADMIN":
                q = q.where(Job.user_id == g.user.id)
            return jsonify(
                page_result(
                    db,
                    q.order_by(Job.created_at.desc()),
                    lambda j: record(
                        j, ("upload_token_hash", "object_key", "lease_owner")
                    ),
                )
            )

    @app.get("/api/operator/jobs/<ident>/source")
    @role("ADMIN", "RTO")
    def original_source(ident):
        from flask import send_file

        with transaction(engine) as db:
            j = fetch(db, Job, ident)
            session_for(db, j.session_id)
            if j.kind != "upload" or not j.object_key:
                abort(
                    404,
                    description="Original uploaded source is unavailable or expired",
                )
            key = j.object_key
        if app.config["STORAGE_MODE"] == "supabase":
            return jsonify(signed_url=g.storage.signed_download(key), expires_in=60)
        path = g.storage.path(key)
        if not path.is_file():
            abort(404, description="Original source missing")
        return send_file(path, conditional=True)

    @app.post("/api/operator/jobs/<ident>/cancel")
    @role("ADMIN", "RTO")
    def cancel(ident):
        with transaction(engine) as db:
            j = fetch(db, Job, ident, True)
            s = session_for(db, j.session_id, True)
            if j.status in ("COMPLETED", "FAILED"):
                abort(409, description="Job already finished")
            j.status = "CANCELLED"
            s.status = "STOPPED"
            audit(db, "CANCEL_JOB", j.id)
        return jsonify(msg="Cancellation requested")

    @app.post("/api/device/candidates")
    def device_ingest():
        # Devices can submit a suspicion only; they cannot confirm or issue memos.
        d = json_body()
        token = request.headers.get("X-Device-Token", "")
        device_id = string(d, "device_id", 60)
        event_id = string(d, "event_id", 80)
        captured = string(d, "captured_at", 40)
        try:
            parsed = datetime.fromisoformat(captured)
            if not parsed.tzinfo:
                raise ValueError()
            stamp = parsed.timestamp()
        except ValueError:
            abort(400, description="UTC capture timestamp required")
        if abs(time.time() - stamp) > 300:
            abort(409, description="Stale device event")
        with transaction(engine) as db:
            device = fetch(db, Device, device_id)
            if not device.active or not secrets.compare_digest(
                device.token_hash, digest(token)
            ):
                abort(403)
            camera = fetch(db, Camera, device.camera_id)
            key = f"device:{device_id}:{event_id}"
            existing = db.scalar(select(Candidate).where(Candidate.event_key == key))
            if existing:
                return jsonify(id=existing.id, status=existing.status)
            rule_name = string(d, "type", 80)
            if rule_name not in BASE_FINES:
                abort(400, description="Unknown rule")
            c = Candidate(
                event_key=key,
                camera_id=camera.id,
                calibration_version=camera.version,
                rule=rule_name,
                location=camera.location,
                explanation=string(d, "explanation", 3000),
                plate=plate(d.get("plate", ""), False),
                captured_at=captured,
                observations={
                    "source": "authenticated_device",
                    "device_id": device.id,
                    "evidence_status": "Device evidence requires operator attachment",
                },
            )
            db.add(c)
            db.flush()
            audit(db, "DEVICE_CANDIDATE", c.id, actor=device.id)
        return jsonify(id=c.id, status="PENDING"), 201


def register_admin_routes(app, engine, throttle):
    from .member3_admin import register_member3_admin

    register_member3_admin(app, engine)

    @app.get("/api/operator/export")
    @role("ADMIN", "RTO")
    def export_csv():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["memo", "plate", "type", "location", "amount", "status"])

        def safe(v):
            value = str(v or "")
            return (
                "'" + value
                if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
            )

        with transaction(engine) as db:
            for m, v in db.execute(
                select(Memo, Violation)
                .join(Violation)
                .order_by(Memo.created_at.desc())
                .limit(10000)
            ):
                writer.writerow(
                    [
                        safe(x)
                        for x in (
                            m.id,
                            v.plate,
                            v.rule,
                            v.location,
                            m.fine_amount,
                            m.status,
                        )
                    ]
                )
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": 'attachment; filename="project-memos.csv"'},
        )

    @app.get("/api/operator/notifications")
    @role("ADMIN", "RTO")
    def notifications():
        with transaction(engine) as db:
            return jsonify(
                page_result(db, select(Outbox).order_by(Outbox.created_at.desc()))
            )


def main():
    from waitress import serve

    app = create_app()
    initialize(app.extensions["engine"])
    serve(
        app,
        host="127.0.0.1" if app.config["APP_ENV"] == "local" else "0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        threads=4,
        max_request_body_size=app.config["MAX_UPLOAD_BYTES"],
    )


if __name__ == "__main__":
    main()
