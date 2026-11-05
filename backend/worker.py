"""Single CPU worker, durable SQL leases, restart-safe idempotent event persistence."""
import os, time, json, tempfile, hashlib, smtplib, socket, threading
from pathlib import Path
from email.message import EmailMessage
import cv2
import numpy as np
from sqlalchemy import select, or_, delete
from .app import create_app
from .db import transaction, initialize
from .models import Job, VideoSession, Candidate, Camera, Service, Outbox, Audit, Revocation, RateLimit, now, uid
from .vision import Detector, MODEL_VERSION, process_frame, annotate, ocr_plate
from .rules import capability
from .camera_sources import validate_sources

class Worker:
    def __init__(self,app):
        self.app=app; self.engine=app.extensions['engine']; self.storage=app.extensions['storage']
        self.temp_root=Path(app.config['DATA_DIR'])/'tmp';self.temp_root.mkdir(parents=True,exist_ok=True)
        self.detector=Detector(app.config['MODEL_PATH']); self.id=uid(); self.last_gc=0
        from .plates import PlateReader
        self.plates=PlateReader()
    def heartbeat(self,db):
        db.merge(Service(id=self.id,heartbeat=time.time(),details={'model_ready':self.detector.ready,'model':MODEL_VERSION,
            'error':self.detector.error,'cpu_threads':int(os.getenv('CV_THREADS','2')),'ocr_ready':self.plates.ready,
            'plate_detector_ready':self.plates.ready,'plate_error':self.plates.error}))
    def claim(self):
        with transaction(self.engine) as db:
            self.heartbeat(db)
            # A lost worker's lease permits a bounded retry. Candidates have stable event keys.
            q=select(Job).where(or_(Job.status=='QUEUED',(Job.status=='RUNNING')&(Job.lease_until<time.time()))).order_by(Job.created_at).with_for_update(skip_locked=True).limit(1)
            j=db.scalar(q)
            if not j: return None
            if j.attempts>=3:
                j.status='FAILED'; j.error='Retry limit reached after interrupted worker'; return None
            j.status='RUNNING'; j.lease_owner=self.id; j.lease_until=time.time()+45; j.attempts+=1
            return j
    def alive(self,job_id,progress=None):
        with transaction(self.engine) as db:
            self.heartbeat(db); j=db.get(Job,job_id)
            if not j or j.status!='RUNNING' or j.lease_owner!=self.id: return False
            s=db.get(VideoSession,j.session_id)
            if not s or s.status!='RUNNING': j.status='CANCELLED'; return False
            if progress is not None: j.progress=progress
            j.lease_until=time.time()+45; return True
    def run_frame(self,job,image,t,seq):
        with transaction(self.engine) as db:
            s=db.get(VideoSession,job.session_id)
            if not s or s.status!='RUNNING': return
            state=s.state; config=s.config; signal=s.result.get('manual_signal'); camera=db.get(Camera,s.camera_id)
            if camera.version!=s.calibration_version: raise ValueError('Calibration changed; restart source')
            if config.get('resolution') and config['resolution']!=[image.shape[1],image.shape[0]]: raise ValueError('Source resolution changed; recalibrate and restart')
            # A gap or rewind invalidates temporal association, including speed transit state.
            if state.get('last_timestamp',-1)>=t: state={}
            if t-state.get('last_timestamp',t)>config.get('max_gap',1.5): state={}
            if job.kind!='frame': signal=None  # No fabricated red state for prerecorded footage or IP inputs.
        tracks,events,state,latency=process_frame(self.detector,image,t,state,config,signal)
        state['last_timestamp']=t
        rendered=annotate(image,tracks,config,t,seq)
        _,encoded=cv2.imencode('.jpg',rendered,[cv2.IMWRITE_JPEG_QUALITY,82])
        preview_key=f'previews/{job.session_id}.jpg'; self.storage.put(preview_key,encoded.tobytes())
        evidence_rows=[]
        for event in events:
            if not self.alive(job.id): return
            # A stable track+rule key suppresses repeated observations within this source session.
            event_key=f'{job.session_id}:{event["track_id"]}:{event["rule"]}'
            cid=hashlib.sha256(event_key.encode()).hexdigest()[:48]
            evidence=self.storage.put(f'evidence/{cid}/snapshot.jpg',encoded.tobytes())
            try: raw,crops=self.plates.read(image,event['box']) if self.plates.ready else ocr_plate(image,event['box'])
            except Exception: raw,crops=[{'status':'unavailable','reason':'Plate recognition failed; manual review required'}],[]
            refs=[evidence]
            for idx,crop in enumerate(crops):
                _,crop_data=cv2.imencode('.jpg',crop)
                refs.append(self.storage.put(f'evidence/{cid}/plate-{idx}.jpg',crop_data.tobytes()))
            evidence_rows.append((event,event_key,cid,refs,raw))
        with transaction(self.engine) as db:
            s=db.get(VideoSession,job.session_id); current=db.get(Job,job.id)
            if not s or s.status!='RUNNING' or not current or current.lease_owner!=self.id: return
            s.state=state; s.processed+=1; s.preview_key=preview_key
            result=dict(s.result); result.update(source_time=t,sequence=seq,tracks=[{k:v for k,v in tr.items() if k in ('id','class','confidence','box')} for tr in tracks],
                latency_ms=round(latency,2),inference_fps=round(1000/max(latency,1),2),
                source_fps=(seq/t if job.kind=='upload' and t>0 else s.received/max(time.time()-datetime_seconds(s.created_at),.001)),model_version=MODEL_VERSION,
                queue_age_ms=round(max(0,time.time()-datetime_seconds(job.created_at))*1000,2) if job.kind=='frame' else None,
                capabilities=capability(config),sampling='Uploads: 2 FPS; webcam: up to 2 FPS; IP: freshest sampled frames',plate_status='Uncertain or unreadable; no owner inferred')
            s.result=result
            for event,key,cid,refs,raw in evidence_rows:
                if db.scalar(select(Candidate.id).where(Candidate.event_key==key)): continue
                db.add(Candidate(id=cid,event_key=key,session_id=s.id,camera_id=s.camera_id,track_id=event['track_id'],rule=event['rule'],
                    calibration_version=s.calibration_version,model_version=MODEL_VERSION,location=camera.location,source_time=t,
                    explanation=event['explanation'],observations={**event,'configuration':config,'timestamp_basis':'source-relative','plate_status':'unreadable/uncertain'},evidence=refs,raw_ocr=raw))
                db.add(Audit(actor=self.id,action='DETECT_CANDIDATE',target=cid,details={'rule':event['rule'],'session':s.id}))
    def process(self,j):
        if not self.detector.ready: raise ValueError(self.detector.error)
        if j.kind=='frame':
            if time.time()-datetime_seconds(j.created_at)>5:
                with transaction(self.engine) as db:
                    row=db.get(Job,j.id); row.status='DROPPED'; db.get(VideoSession,j.session_id).dropped+=1
                return
            image=cv2.imdecode(np.frombuffer(self.storage.get(j.object_key),np.uint8),cv2.IMREAD_COLOR)
            if image is None or max(image.shape[:2])>1280: raise ValueError('Invalid frame')
            self.run_frame(j,image,j.source_ts,j.seq)
        elif j.kind=='upload':
            with tempfile.TemporaryDirectory(prefix='e-memo-',dir=self.temp_root) as temp:
                path=self.storage.materialize(j.object_key,Path(temp)/'input.video')
                capture=cv2.VideoCapture(str(path))
                try:
                    fps=capture.get(cv2.CAP_PROP_FPS); count=capture.get(cv2.CAP_PROP_FRAME_COUNT)
                    width=capture.get(cv2.CAP_PROP_FRAME_WIDTH); height=capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    if not capture.isOpened() or max(width,height)>4096 or min(width,height)<100:
                        raise ValueError('Invalid video: supported codec and 100–4096px dimensions required')
                    # Restart from frame zero after interruption so tracking/event keys replay deterministically.
                    with transaction(self.engine) as db: db.get(VideoSession,j.session_id).state={}
                    # WebM may report its 1000 Hz time base as FPS. Use decoded PTS,
                    # not CAP_PROP_FPS to establish the source timeline.
                    idx=0; previous_ts=-1; next_sample=0; first_pts=None
                    last_lease=0
                    while True:
                        if time.monotonic()-last_lease>1:
                            hint_duration=count/fps if fps>0 and count>0 else 600
                            if not self.alive(j.id,max(0,min(.99,previous_ts/max(hint_duration,.1)))): return
                            last_lease=time.monotonic()
                        ok=capture.grab()
                        if not ok: break
                        pts=capture.get(cv2.CAP_PROP_POS_MSEC)/1000
                        if not np.isfinite(pts) or pts<0: raise ValueError('Source timestamps unavailable; calibrated movement evaluation cannot run')
                        if first_pts is None: first_pts=pts
                        stamp=pts-first_pts
                        if stamp>600 or idx>72000: raise ValueError('Video exceeds 10-minute or 72000-frame limit')
                        if idx>0 and stamp<=previous_ts: raise ValueError('Non-monotonic source timestamps; use a timestamp-preserving transcode')
                        if stamp>=next_sample:
                            ok,image=capture.retrieve()
                            if not ok: raise ValueError('Video decoding failed')
                            self.run_frame(j,image,stamp,idx); next_sample=stamp+.5
                        previous_ts=stamp
                        idx+=1
                    if idx<2: raise ValueError('Video has fewer than two decodable frames')
                    with transaction(self.engine) as db:
                        session=db.get(VideoSession,j.session_id); session.received=idx; session.dropped=max(0,idx-session.processed)
                finally: capture.release()
        elif j.kind=='ip': self.ip_camera(j)
        else: raise ValueError('Unsupported job type')
        with transaction(self.engine) as db:
            current=db.get(Job,j.id)
            if current.status=='RUNNING' and current.lease_owner==self.id:
                current.status='COMPLETED'; current.progress=1; current.finished_at=now()
                if j.kind!='frame': db.get(VideoSession,j.session_id).status='COMPLETED'
    def ip_camera(self,j):
        with transaction(self.engine) as db:
            s=db.get(VideoSession,j.session_id); c=db.get(Camera,s.camera_id)
            source=validate_sources(self.app.config['CAMERA_SOURCES']).get(c.source_key)
        from urllib.parse import urlparse
        if not isinstance(source,str) or urlparse(source).scheme not in ('rtsp','rtsps'): raise ValueError('Camera gateway is not configured')
        # Only operator-provisioned exact URLs from environment are ever opened. No URL from an API body is fetched.
        # A capture thread retains just the freshest frame; it never runs inference or touches the database.
        cap=cv2.VideoCapture(source,cv2.CAP_FFMPEG,[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,5000,cv2.CAP_PROP_READ_TIMEOUT_MSEC,3000])
        if not cap.isOpened(): cap.release(); raise ValueError('Authorized camera is unreachable; check gateway connectivity')
        slot={'frame':None,'seq':0,'timestamp':0,'failed':False}; lock=threading.Lock(); stopped=threading.Event(); start=time.monotonic()
        def reader():
            while not stopped.is_set():
                ok,frame=cap.read()
                if not ok: slot['failed']=True; break
                if max(frame.shape[:2])>4096: slot['failed']=True; break
                with lock: slot.update(frame=frame,seq=slot['seq']+1,timestamp=time.monotonic()-start)
        thread=threading.Thread(target=reader,daemon=True); thread.start(); previous=0
        try:
            while time.monotonic()-start<900:
                if not self.alive(j.id): return
                if slot['failed']: raise ValueError('Camera disconnected; restart the configured source to reconnect')
                with lock: frame=slot['frame']; seq=slot['seq']; stamp=slot['timestamp']
                if frame is not None and seq!=previous:
                    with transaction(self.engine) as db:
                        s=db.get(VideoSession,j.session_id); s.received+=seq-previous; s.dropped+=max(0,seq-previous-1); s.heartbeat=time.time()
                    self.run_frame(j,frame,stamp,seq); previous=seq
                time.sleep(.5)
        finally:
            stopped.set(); thread.join(timeout=4); cap.release()
    def notify(self):
        with transaction(self.engine) as db:
            row=db.scalar(select(Outbox).where(Outbox.status.in_(['QUEUED','FAILED']),Outbox.next_attempt<=time.time(),Outbox.attempts<3,Outbox.lease_until<time.time()).with_for_update(skip_locked=True).limit(1))
            if not row: return
            row.attempts+=1; row.lease_until=time.time()+60; ident=row.id; recipient=row.recipient; body=row.body
        try:
            allowed={v.strip().lower() for v in os.getenv('NOTIFICATION_RECIPIENT_ALLOWLIST','').split(',') if v.strip()}
            if self.app.config['NOTIFICATION_MODE']!='smtp' or recipient.lower() not in allowed: raise ValueError('Delivery disabled or recipient not explicitly verified')
            if not all(os.getenv(x) for x in ('SMTP_HOST','SMTP_USER','SMTP_PASSWORD','SMTP_FROM')): raise ValueError('SMTP setup incomplete')
            msg=EmailMessage(); msg['From']=os.environ['SMTP_FROM']; msg['To']=recipient; msg['Subject']='e-Memo project demonstration'; msg['Message-ID']=f'<{ident}@e-memo-project.local>'; msg.set_content(body)
            with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=15) as server:
                server.starttls(); server.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']); server.send_message(msg)
            status='SENT'; error=None
        except Exception: status='FAILED'; error='Delivery unavailable; check verified recipient and SMTP configuration'
        with transaction(self.engine) as db:
            row=db.get(Outbox,ident); row.status=status; row.error=error; row.next_attempt=time.time()+min(3600,60*2**row.attempts); row.lease_until=0
    def cleanup(self):
        if time.time()-self.last_gc<60: return
        self.last_gc=time.time()
        with transaction(self.engine) as db:
            db.execute(delete(Revocation).where(Revocation.expires<time.time()))
            db.execute(delete(RateLimit).where(RateLimit.window<time.time()-86400))
            db.execute(delete(Service).where(Service.heartbeat<time.time()-3600))
            # Expire stale webcam sessions, including abandoned browser tabs.
            for s in db.scalars(select(VideoSession).where(VideoSession.kind=='webcam',VideoSession.status=='RUNNING',VideoSession.heartbeat<time.time()-30)): s.status='TIMED_OUT'
            old=list(db.scalars(select(Job).where(Job.kind=='frame',Job.status.in_(['COMPLETED','DROPPED','FAILED','CANCELLED'])).limit(100)))
            keys=[j.object_key for j in old if j.object_key]
            for j in db.scalars(select(Job).where(Job.status.in_(['AWAITING_UPLOAD','UPLOADING','UPLOADED']),Job.upload_expires<time.time())):
                j.status='EXPIRED'
                if j.object_key: keys.append(j.object_key)
            for j in old: db.delete(j)
        for key in keys:
            try: self.storage.delete(key)
            except Exception: pass
    def tick(self):
        j=self.claim()
        if j:
            try: self.process(j)
            except Exception as exc:
                # Known operational messages are safe; never persist stream URLs or raw exceptions.
                message=str(exc) if isinstance(exc,ValueError) else 'Video processing failed; verify media codec, storage and model setup'
                with transaction(self.engine) as db:
                    current=db.get(Job,j.id)
                    if current and current.lease_owner==self.id and current.status=='RUNNING':
                        current.status='FAILED'; current.error=message[:200]; current.finished_at=now()
                        s=db.get(VideoSession,j.session_id); s.status='FAILED'; s.result={**s.result,'error':message[:200]}
        self.notify(); self.cleanup(); return bool(j)
def datetime_seconds(value):
    from datetime import datetime
    return datetime.fromisoformat(value).timestamp()
def main():
    app=create_app(); initialize(app.extensions['engine']); worker=Worker(app)
    print('Video worker ready' if worker.detector.ready else worker.detector.error,flush=True)
    while True:
        if not worker.tick(): time.sleep(.25)
if __name__=='__main__': main()
