"""Member 3 scoped case reporting, analytics and government privacy projection."""

import hashlib, re
from collections import Counter
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, g, abort
from sqlalchemy import select, func, or_
from .models import *
from .db import transaction


def register_member3_reporting(app, engine):
    from .app import role, record, page_query

    def demo_expr():
        return or_(
            Candidate.model_version.like("synthetic%"),
            Candidate.event_key.like("showcase-%"),
            Candidate.id.in_(select(CaseMetadata.id).where(CaseMetadata.is_demo == 1)),
        )

    def scoped():
        q = select(Candidate)
        if g.user.role == "USER":
            q = q.join(Violation, Violation.candidate_id == Candidate.id).where(
                Violation.plate.in_(
                    select(Link.plate).where(
                        Link.user_id == g.user.id, Link.status == "APPROVED"
                    )
                )
            )
        return q

    def filtered(q, db):
        args = request.args
        if args.get("scope") == "demo":
            q = q.where(demo_expr())
        elif args.get("scope") == "live":
            q = q.where(~demo_expr())
        if args.get("status") and args["status"] != "ALL":
            q = q.where(Candidate.status == args["status"])
        if args.get("type"):
            q = q.where(Candidate.rule == args["type"])
        if args.get("location"):
            q = q.where(Candidate.location == args["location"])
        if args.get("camera"):
            q = q.where(Candidate.camera_id == args["camera"])
        if args.get("q"):
            term = args["q"][:100].strip()
            fields = [
                Candidate.id.contains(term),
                Candidate.rule.contains(term),
                Candidate.location.contains(term),
            ]
            if re.fullmatch(r"EM-[0-9A-Fa-f]{1,7}", term, re.IGNORECASE):
                prefix = term[3:].lower()
                matches = [
                    ident
                    for ident in db.scalars(q.with_only_columns(Candidate.id))
                    if hashlib.sha256(ident.encode()).hexdigest().startswith(prefix)
                ]
                fields.append(Candidate.id.in_(matches))
            if g.user.role != "GOVT":
                fields.append(Candidate.plate.contains(term.upper().replace(" ", "")))
            q = q.where(or_(*fields))
        for key, lower in [("from", True), ("to", False)]:
            if args.get(key):
                try:
                    dt = datetime.fromisoformat(args[key].replace("Z", "+00:00"))
                    if not dt.tzinfo:
                        raise ValueError()
                    stamp = dt.astimezone(timezone.utc).isoformat()
                except ValueError:
                    abort(400, description="A date and timezone are required")
                q = q.where(
                    Candidate.created_at >= stamp
                    if lower
                    else Candidate.created_at < stamp
                )
        return q

    def profile(db, number):
        v = db.get(VehicleProfile, number) if number else None
        link = (
            db.scalar(
                select(Link).where(Link.plate == number, Link.status == "APPROVED")
            )
            if number
            else None
        )
        user = db.get(User, link.user_id) if link else None
        return {
            "plate": number,
            "model": v.model if v else "",
            "vehicle_class": v.vehicle_class if v else "",
            "color": v.color if v else "",
            "owner_name": (
                v.owner_display_name
                if v and v.owner_display_name
                else user.full_name if user else None
            ),
            "owner_email": user.email if user else None,
            "owner_phone": (
                v.contact_phone
                if v and v.contact_phone
                else user.phone_number if user else None
            ),
            "address": v.address if v and user else None,
            "ownership_verified": bool(link),
            "is_demo": bool(v and v.is_demo),
        }

    def serialize(db, c, detail=False):
        meta = db.get(CaseMetadata, c.id)
        is_demo = bool(
            (meta and meta.is_demo)
            or c.model_version.startswith("synthetic")
            or c.event_key.startswith("showcase-")
        )
        v = db.scalar(select(Violation).where(Violation.candidate_id == c.id))
        m = db.scalar(select(Memo).where(Memo.violation_id == v.id)) if v else None
        payment = (
            db.scalar(select(Payment).where(Payment.memo_id == m.id)) if m else None
        )
        dispute = (
            db.scalar(select(Dispute).where(Dispute.memo_id == m.id)) if m else None
        )
        asset = db.get(DatasetAsset, meta.asset_id) if meta and meta.asset_id else None
        government = g.user.role == "GOVT"
        p = profile(db, c.plate) if not government else None
        data = {
            "id": c.id,
            "reference": "EM-" + hashlib.sha256(c.id.encode()).hexdigest()[:7].upper(),
            "type": c.rule,
            "location": c.location,
            "status": c.status,
            "created_at": c.created_at,
            "source_time": c.source_time,
            "captured_at": c.captured_at,
            "plate": None if government else c.plate,
            "vehicle": p,
            "is_demo": is_demo,
            "source_label": (
                "Dataset example"
                if asset
                else (
                    "Practice example"
                    if is_demo
                    else "Video analysis" if c.session_id else "Manual report"
                )
            ),
            "explanation": (
                (
                    "An RTO case for "
                    + c.rule
                    + ". Identifiable evidence remains restricted to authorized reviewers."
                )
                if government
                else c.explanation
            ),
            "evidence_count": len(c.evidence),
            "memo_id": m.id if m else None,
            "fine_amount": m.fine_amount if m else None,
            "memo_status": m.status if m else None,
            "payment_mode": payment.mode if payment else None,
            "dispute_status": dispute.status if dispute else None,
            "next_action": (
                "Review evidence"
                if c.status == "PENDING"
                else (
                    "Add missing evidence"
                    if c.status == "NEEDS_EVIDENCE"
                    else (
                        "Resolve dispute"
                        if m and m.status == "DISPUTED"
                        else (
                            "Await sandbox payment"
                            if m and m.status == "UNPAID"
                            else "Case complete"
                        )
                    )
                )
            ),
            "dataset": (
                {
                    "title": asset.title,
                    "license": asset.license,
                    "source_url": asset.source_url,
                    "attribution": asset.attribution,
                    "annotations": asset.annotations,
                }
                if asset
                else None
            ),
        }
        if detail:
            data.update(
                review_reason=None if government else c.review_reason,
                rule_version=c.rule_version,
                calibration_version=c.calibration_version,
                model_version=c.model_version,
                observations={} if government else c.observations,
                ocr=[] if government else c.raw_ocr,
                reviewer=None if government else c.reviewer,
                payment=record(payment) if payment and not government else None,
                dispute=record(dispute) if dispute and not government else None,
                memo=record(m) if m else None,
                evidence=(
                    []
                    if government
                    else [
                        {**e, "url": f"/api/candidates/{c.id}/evidence/{i}"}
                        for i, e in enumerate(c.evidence)
                    ]
                ),
            )
            targets = [c.id] + ([m.id] if m else []) + ([dispute.id] if dispute else [])
            events = list(
                db.scalars(
                    select(Audit)
                    .where(Audit.target.in_(targets))
                    .order_by(Audit.created_at)
                )
            )
            data["timeline"] = [
                {
                    "action": e.action.replace("_", " ").title(),
                    "time": e.created_at,
                    "reason": (
                        ""
                        if government
                        else e.details.get("reason") or e.details.get("note") or ""
                    ),
                    "actor": (
                        None
                        if government or g.user.role == "USER"
                        else (
                            db.get(User, e.actor).full_name
                            if db.get(User, e.actor)
                            else "System"
                        )
                    ),
                }
                for e in events
            ]
            if not data["timeline"]:
                data["timeline"] = [
                    {
                        "action": "Case recorded",
                        "time": c.created_at,
                        "reason": data["explanation"],
                        "actor": "System",
                    }
                ]
        return data

    @app.get("/api/cases")
    @role("USER", "RTO", "ADMIN", "GOVT")
    def cases():
        with transaction(engine) as db:
            q = filtered(scoped(), db)
            paged, page, size = page_query(q.order_by(Candidate.created_at.desc()))
            return jsonify(
                items=[serialize(db, c) for c in db.scalars(paged)],
                page=page,
                size=size,
                total=db.scalar(select(func.count()).select_from(q.subquery())),
            )

    @app.get("/api/case-filters")
    @role("USER", "RTO", "ADMIN", "GOVT")
    def case_filters():
        with transaction(engine) as db:
            ids = filtered(scoped(), db).with_only_columns(Candidate.id)
            return jsonify(
                locations=list(
                    db.scalars(
                        select(Candidate.location)
                        .where(Candidate.id.in_(ids))
                        .distinct()
                        .order_by(Candidate.location)
                    )
                ),
                types=list(
                    db.scalars(
                        select(Candidate.rule)
                        .where(Candidate.id.in_(ids))
                        .distinct()
                        .order_by(Candidate.rule)
                    )
                ),
            )

    @app.get("/api/cases/<ident>")
    @role("USER", "RTO", "ADMIN", "GOVT")
    def case(ident):
        with transaction(engine) as db:
            c = db.scalar(scoped().where(Candidate.id == ident))
            if not c:
                abort(404, description="Case not found")
            return jsonify(serialize(db, c, True))

    @app.get("/api/overview")
    @role("USER", "RTO", "ADMIN", "GOVT")
    def overview():
        with transaction(engine) as db:
            q = filtered(scoped(), db)
            ids = q.with_only_columns(Candidate.id).order_by(None)
            total = db.scalar(select(func.count()).select_from(q.subquery()))
            statuses = dict(
                db.execute(
                    select(Candidate.status, func.count())
                    .where(Candidate.id.in_(ids))
                    .group_by(Candidate.status)
                ).all()
            )
            types = [
                {"name": a, "value": n}
                for a, n in db.execute(
                    select(Candidate.rule, func.count())
                    .where(Candidate.id.in_(ids))
                    .group_by(Candidate.rule)
                )
            ]
            locations = [
                {"name": a, "value": n}
                for a, n in db.execute(
                    select(Candidate.location, func.count())
                    .where(Candidate.id.in_(ids))
                    .group_by(Candidate.location)
                )
            ]
            dates = Counter(
                datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                .astimezone(timezone(timedelta(hours=5, minutes=30)))
                .date()
                .isoformat()
                for stamp in db.scalars(
                    select(Candidate.created_at).where(Candidate.id.in_(ids))
                )
            )
            trend = [{"date": a, "cases": n} for a, n in sorted(dates.items())]
            mids = (
                select(Memo.id).join(Violation).where(Violation.candidate_id.in_(ids))
            )
            money = {s: 0 for s in ("UNPAID", "SANDBOX_PAID", "DISPUTED", "VOID")}
            for state, value in db.execute(
                select(Memo.status, func.sum(Memo.fine_amount))
                .where(Memo.id.in_(mids))
                .group_by(Memo.status)
            ):
                money[state] = value
            recent = list(db.scalars(q.order_by(Candidate.created_at.desc()).limit(5)))
            return jsonify(
                total=total,
                pending=statuses.get("PENDING", 0),
                needs_evidence=statuses.get("NEEDS_EVIDENCE", 0),
                confirmed=statuses.get("CONFIRMED", 0),
                rejected=statuses.get("REJECTED", 0),
                statuses=statuses,
                money=money,
                types=types,
                locations=locations,
                trend=trend,
                demos=db.scalar(
                    select(func.count()).select_from(q.where(demo_expr()).subquery())
                ),
                disputes=db.scalar(
                    select(func.count())
                    .select_from(Dispute)
                    .where(Dispute.memo_id.in_(mids), Dispute.status == "PENDING")
                ),
                vehicles=(
                    db.scalar(
                        select(func.count())
                        .select_from(Link)
                        .where(Link.user_id == g.user.id, Link.status == "APPROVED")
                    )
                    if g.user.role == "USER"
                    else db.scalar(select(func.count()).select_from(VehicleProfile))
                ),
                recent=[serialize(db, c) for c in recent],
                timezone="Asia/Kolkata",
                financial_mode="sandbox",
            )

    return profile
