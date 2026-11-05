"""Human-readable casebook and role-specific overview over the canonical database."""

import hashlib, time, re
from collections import Counter
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, g, abort, Response
from sqlalchemy import select, func, or_, and_
from .models import *
from .db import transaction


def register_experience(app, engine):
    # Import after app helpers are defined; no second authorization system.
    from .app import (
        role,
        fetch,
        record,
        owner,
        audit,
        json_body,
        string,
        plate,
        page_query,
    )
    from .member3_reporting import register_member3_reporting

    profile = register_member3_reporting(app, engine)

    @app.get("/api/registry")
    @role("RTO", "ADMIN")
    def registry():
        with transaction(engine) as db:
            q = select(VehicleProfile)
            if request.args.get("q"):
                term = request.args["q"][:100]
                q = q.where(
                    or_(
                        VehicleProfile.id.contains(term.upper()),
                        VehicleProfile.owner_display_name.contains(term),
                        VehicleProfile.model.contains(term),
                    )
                )
            paged, page, size = page_query(q.order_by(VehicleProfile.id))
            result = []
            for v in db.scalars(paged):
                p = profile(db, v.id)
                p["cases"] = db.scalar(
                    select(func.count())
                    .select_from(Candidate)
                    .where(Candidate.plate == v.id)
                )
                p["outstanding"] = db.scalar(
                    select(func.coalesce(func.sum(Memo.fine_amount), 0))
                    .join(Violation)
                    .where(Violation.plate == v.id, Memo.status == "UNPAID")
                )
                result.append(p)
            return jsonify(
                items=result,
                total=db.scalar(select(func.count()).select_from(q.subquery())),
                page=page,
                size=size,
            )

    @app.post("/api/registry")
    @role("RTO", "ADMIN")
    def save_vehicle():
        d = json_body()
        number = plate(d.get("plate", ""))
        with transaction(engine) as db:
            p = db.get(VehicleProfile, number)
            if not p:
                p = VehicleProfile(id=number)
                db.add(p)
            for key, limit in [
                ("model", 120),
                ("vehicle_class", 30),
                ("color", 40),
                ("registration_reference", 100),
                ("owner_display_name", 150),
                ("contact_phone", 30),
                ("address", 300),
            ]:
                setattr(p, key, string(d, key, limit, False))
            audit(
                db,
                "UPDATE_VEHICLE_DIRECTORY",
                number,
                {
                    "note": "Profile updated; ownership approval remains a separate verified transition"
                },
            )
        return (
            jsonify(msg="Vehicle details saved. Ownership approval is separate."),
            201,
        )

    @app.get("/api/datasets")
    @role("RTO", "ADMIN")
    def datasets():
        with transaction(engine) as db:
            return jsonify(
                items=[
                    {
                        **record(a, ("object_key",)),
                        "image_url": f"/api/datasets/{a.id}/image",
                    }
                    for a in db.scalars(
                        select(DatasetAsset).order_by(
                            DatasetAsset.category, DatasetAsset.id
                        )
                    )
                ],
                demo_enabled=app.config.get("APP_ENV") == "local",
                note="Dataset images have no link to actual owners. Any associated demonstration identity is fictional.",
            )

    @app.get("/api/datasets/<ident>/image")
    @role("RTO", "ADMIN")
    def dataset_image(ident):
        with transaction(engine) as db:
            asset = fetch(db, DatasetAsset, ident)
        data = g.storage.get(asset.object_key)
        if hashlib.sha256(data).hexdigest() != asset.sha256:
            abort(409, description="Dataset evidence checksum mismatch")
        return Response(data, mimetype="image/jpeg")

    @app.post("/api/datasets/<ident>/example")
    @role("RTO", "ADMIN")
    def dataset_example(ident):
        if app.config.get("APP_ENV") != "local":
            abort(
                403,
                description="Example cases are restricted to local demonstration mode",
            )
        d = json_body()
        event = request.headers.get("Idempotency-Key", "")
        if not 8 <= len(event) <= 80:
            abort(400, description="A unique request reference is required")
        with transaction(engine) as db:
            asset = fetch(db, DatasetAsset, ident)
            chosen = plate(
                d.get(
                    "plate",
                    "GJ00DM1010" if "helmet" in asset.category else "GJ00DM1001",
                )
            )
            v = db.get(VehicleProfile, chosen)
            if not v or not v.is_demo:
                abort(
                    400,
                    description="Choose a fictional demonstration vehicle from the directory",
                )
            key = "showcase-import:" + g.user.id + ":" + event
            c = db.scalar(select(Candidate).where(Candidate.event_key == key))
            if c:
                return jsonify(id=c.id)
            c = Candidate(
                event_key=key,
                rule=(
                    "Helmet Violation"
                    if "helmet" in asset.category
                    else "restricted_zone"
                ),
                plate=chosen,
                location=string(d, "location", 150, False)
                or "Dataset demonstration junction",
                model_version="dataset-annotation-example",
                explanation="Dataset-backed practice case. The source annotation is shown for review; the vehicle/owner link is fictional and is not an identification of the person pictured.",
                observations={
                    "mode": "DATASET_DEMONSTRATION",
                    "dataset_annotations": asset.annotations,
                    "fictional_plate_assignment": chosen,
                },
                evidence=[
                    {
                        "key": asset.object_key,
                        "sha256": asset.sha256,
                        "content_type": "image/jpeg",
                    }
                ],
            )
            db.add(c)
            db.flush()
            db.add(
                CaseMetadata(
                    id=c.id,
                    is_demo=1,
                    asset_id=asset.id,
                    note="Fictional example identity; dataset image used with attribution",
                )
            )
            audit(
                db,
                "CREATE_DATASET_EXAMPLE",
                c.id,
                {"asset": asset.id, "note": "Fictional demonstration identity only"},
            )
        return jsonify(id=c.id), 201

    @app.post("/api/samples/rush-hour/run")
    @role("RTO", "ADMIN")
    def run_sample():
        if app.config.get("APP_ENV") != "local":
            abort(
                403,
                description="Included sample is available in local demonstration mode",
            )
        from pathlib import Path
        from .app import ROOT

        path = ROOT / "samples" / "rush-hour.webm"
        if not path.is_file():
            abort(503, description="Included traffic sample has not been downloaded")
        with transaction(engine) as db:
            ready = db.scalar(
                select(Service).where(Service.heartbeat > time.time() - 30)
            )
            if not ready or not ready.details.get("model_ready"):
                abort(
                    503, description="Start the video worker before running the sample"
                )
            camera = db.get(Camera, "demo-camera")
            if not camera:
                abort(409, description="Load the local demonstration data first")
            active = db.scalar(
                select(Job).where(
                    Job.user_id == g.user.id,
                    Job.kind == "upload",
                    Job.status.in_(["QUEUED", "RUNNING"]),
                )
            )
            if active:
                return jsonify(job_id=active.id, session_id=active.session_id), 202
            s = VideoSession(
                user_id=g.user.id,
                camera_id=camera.id,
                kind="upload",
                config=camera.config,
                calibration_version=camera.version,
            )
            db.add(s)
            db.flush()
            jid = uid()
            key = f"uploads/{jid}.webm"
            g.storage.put(key, path.read_bytes(), "video/webm")
            db.add(
                Job(
                    id=jid,
                    user_id=g.user.id,
                    session_id=s.id,
                    kind="upload",
                    status="QUEUED",
                    object_key=key,
                    bytes=path.stat().st_size,
                )
            )
            audit(
                db,
                "RUN_INCLUDED_SAMPLE",
                s.id,
                {
                    "note": "CC0 prerecorded sample; configured demonstration zone, not an actual enforcement claim"
                },
            )
        return jsonify(job_id=jid, session_id=s.id), 202
