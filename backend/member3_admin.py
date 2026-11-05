"""Member 3 administration and government reporting; uses the shared auth system."""
import secrets
from datetime import datetime,timezone
from flask import request,jsonify,g,abort
from sqlalchemy import select,func
from .models import *
from .db import transaction

def register_member3_admin(app,engine):
    from .app import role,record,page_result,fetch,json_body,string,audit,number,digest,BASE_FINES
    @app.get('/api/gov/analytics')
    @role('GOVT','ADMIN','RTO')
    def analytics():
        # Bounds are UTC instants supplied by the UI after applying Asia/Kolkata dates.
        filters=[]
        for key,operator in (('from',True),('to',False)):
            if request.args.get(key):
                try:
                    dt=datetime.fromisoformat(request.args[key].replace('Z','+00:00'))
                    if not dt.tzinfo: raise ValueError()
                    stamp=dt.astimezone(timezone.utc).isoformat()
                except ValueError: abort(400,description='Use ISO dates with a timezone')
                filters.append(Violation.created_at>=stamp if operator else Violation.created_at<stamp)
        if request.args.get('location'): filters.append(Violation.location==request.args['location'][:150])
        if request.args.get('type'): filters.append(Violation.rule==request.args['type'][:80])
        with transaction(engine) as db:
            q=select(Violation).where(*filters)
            if request.args.get('camera_id'): q=q.join(Candidate).where(Candidate.camera_id==request.args['camera_id'])
            ids=q.with_only_columns(Violation.id)
            memos_q=select(Memo).where(Memo.violation_id.in_(ids))
            def count(status): return db.scalar(select(func.count()).select_from(memos_q.where(Memo.status==status).subquery()))
            revenue=db.scalar(select(func.coalesce(func.sum(Memo.fine_amount),0)).where(Memo.violation_id.in_(ids),Memo.status=='SANDBOX_PAID'))
            areas=[{'name':a,'value':n} for a,n in db.execute(select(Violation.location,func.count()).where(Violation.id.in_(ids)).group_by(Violation.location))]
            types=[{'name':a,'value':n} for a,n in db.execute(select(Violation.rule,func.count()).where(Violation.id.in_(ids)).group_by(Violation.rule))]
            # Portable grouping; DB does the aggregate and returns no citizen identities.
            month=func.substr(Violation.created_at,1,7)
            trends=[{'month':a,'violations':n} for a,n in db.execute(select(month,func.count()).where(Violation.id.in_(ids)).group_by(month).order_by(month))]
            pending=select(Candidate).where(Candidate.status.in_(['PENDING','NEEDS_EVIDENCE']))
            if request.args.get('location'): pending=pending.where(Candidate.location==request.args['location'])
            if request.args.get('type'): pending=pending.where(Candidate.rule==request.args['type'])
            if request.args.get('camera_id'): pending=pending.where(Candidate.camera_id==request.args['camera_id'])
            for key,op in (('from',True),('to',False)):
                if request.args.get(key):
                    val=datetime.fromisoformat(request.args[key].replace('Z','+00:00')).astimezone(timezone.utc).isoformat()
                    pending=pending.where(Candidate.created_at>=val if op else Candidate.created_at<val)
            return jsonify(kpi={'total_violations':db.scalar(select(func.count()).select_from(q.subquery())),
                'total_memos':db.scalar(select(func.count()).select_from(memos_q.subquery())),'total_revenue':revenue,'verified_real_revenue':0,
                'pending_count':count('UNPAID'),'paid_count':count('SANDBOX_PAID'),'pending_candidates':db.scalar(select(func.count()).select_from(pending.subquery()))},
                area_wise=areas,types=types,monthly_trends=trends,timezone='Asia/Kolkata',revenue_mode='SANDBOX ONLY')
    @app.get('/api/admin/users')
    @role('ADMIN')
    def users():
        with transaction(engine) as db: return jsonify(page_result(db,select(User).order_by(User.email),lambda u:record(u,('password_hash','token_version'))))
    @app.patch('/api/admin/users/<ident>')
    @role('ADMIN')
    def provision(ident):
        d=json_body(); new_role=d.get('role')
        if new_role not in ('USER','RTO','GOVT','ADMIN'): abort(400,description='Invalid role')
        reason=string(d,'reason',1000)
        with transaction(engine) as db:
            u=fetch(db,User,ident,True)
            if u.id==g.user.id: abort(409,description='Use another administrator to change your own role')
            old=u.role; u.role=new_role; u.token_version+=1
            audit(db,'PROVISION_ROLE',u.id,{'from':old,'to':new_role,'reason':reason})
        return jsonify(msg='Role provisioned; existing sessions revoked')
    @app.get('/api/admin/audit')
    @role('ADMIN')
    def audit_log():
        with transaction(engine) as db: return jsonify(page_result(db,select(Audit).order_by(Audit.created_at.desc())))
    @app.get('/api/admin/policy')
    @role('ADMIN')
    def policy():
        with transaction(engine) as db:
            value=db.get(Setting,'fine_policy')
            return jsonify(value.value if value else {'version':'project-demo-1','bases':BASE_FINES})
    @app.put('/api/admin/policy')
    @role('ADMIN')
    def set_policy():
        d=json_body(); bases=d.get('bases')
        if not isinstance(bases,dict) or set(bases)!=set(BASE_FINES): abort(400,description='Supply each supported rule base')
        for key,val in bases.items(): number(val,0,100000,'Base fine')
        version='project-demo-'+uid()[:8]
        with transaction(engine) as db:
            db.merge(Setting(id='fine_policy',value={'version':version,'bases':bases})); audit(db,'UPDATE_DEMO_POLICY',version,{'bases':bases})
        return jsonify(msg='Demo fine policy version saved',version=version)
    @app.post('/api/admin/devices')
    @role('ADMIN')
    def create_device():
        d=json_body(); token=secrets.token_urlsafe(40)
        with transaction(engine) as db:
            c=fetch(db,Camera,d.get('camera_id')); dev=Device(camera_id=c.id,token_hash=digest(token)); db.add(dev); db.flush(); audit(db,'CREATE_DEVICE',dev.id)
        return jsonify(id=dev.id,token=token,msg='Store this credential securely; it is shown once'),201
    @app.delete('/api/admin/devices/<ident>')
    @role('ADMIN')
    def revoke_device(ident):
        with transaction(engine) as db: fetch(db,Device,ident,True).active=0; audit(db,'REVOKE_DEVICE',ident)
        return jsonify(msg='Device revoked')

def register_member3_health(app,engine,model_health):
    from .app import role
    @app.get('/api/operator/health')
    @role('ADMIN','RTO')
    def operator_health():
        with transaction(engine) as db:
            return jsonify(**model_health(db),queued_jobs=db.scalar(select(func.count()).select_from(Job).where(Job.status=='QUEUED')),
                           active_sessions=db.scalar(select(func.count()).select_from(VideoSession).where(VideoSession.status=='RUNNING')),
                           storage=app.config['STORAGE_MODE'],notification_mode=app.config['NOTIFICATION_MODE'])
