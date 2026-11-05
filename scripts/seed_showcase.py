"""Local dataset-backed practice cases with fictional owners; preserves user edits."""
import json,hashlib,argparse
from pathlib import Path
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from backend.db import make_engine,initialize,transaction
from backend.models import *
from backend.storage import Storage
from .seed_local_demo import seed,ROOT

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data-dir',default=str(ROOT/'data'));args=parser.parse_args()
    data=Path(args.data_dir).resolve();seed(data)
    manifest=json.loads((ROOT/'samples/showcase/manifest.json').read_text(encoding='utf-8'))
    storage=Storage({'DATA_DIR':str(data),'STORAGE_MODE':'local'});engine=make_engine('sqlite:///'+(data/'traffic.db').as_posix());initialize(engine)
    with transaction(engine) as db:
        primary=db.scalar(select(User).where(User.email=='citizen.demo@preksha.test'));other=db.scalar(select(User).where(User.email=='other.demo@preksha.test'));reviewer=db.scalar(select(User).where(User.email=='rto.demo@preksha.test'))
        for number,model,kind,color,name,user in [('GJ00DM1001','Hyundai i20','car','White','Aarav Patel (fictional)',primary),
            ('GJ00DM1002','Maruti Suzuki Swift','car','Blue','Aarav Patel (fictional)',primary),
            ('GJ00DM1010','Honda Activa 125','motorcycle','Grey','Aarav Patel (fictional)',primary),
            ('GJ00DM2001','Tata Nexon','car','Red','Neha Shah (fictional)',other),
            ('GJ00DM2010','Bajaj Pulsar 150','motorcycle','Black','Neha Shah (fictional)',other)]:
            if not db.get(VehicleProfile,number): db.add(VehicleProfile(id=number,model=model,vehicle_class=kind,color=color,
                owner_display_name=name,contact_phone='DEMO CONTACT ONLY',address='Fictional demonstration address, Ahmedabad',registration_reference='DEMO-RC-'+number[-4:],is_demo=1))
            if number.endswith('1010') or number.endswith('2010'):
                if not db.scalar(select(Link.id).where(Link.plate==number,Link.user_id==user.id)):
                    db.add(Link(user_id=user.id,plate=number,status='APPROVED',proof='Explicitly fictional local showcase ownership',reviewer=reviewer.id,reason='Fictional showcase fixture, not government verification'))
        db.flush()
        for c in db.scalars(select(Candidate).where(Candidate.model_version.like('synthetic%'))):
            if not db.get(CaseMetadata,c.id): db.add(CaseMetadata(id=c.id,is_demo=1,note='Local practice fixture'))
        for i,asset in enumerate(manifest):
            raw=(ROOT/asset['file']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=asset['sha256']:raise RuntimeError('Dataset checksum mismatch')
            key='datasets/'+asset['id']+'.jpg';storage.put(key,raw)
            if not db.get(DatasetAsset,asset['id']):
                db.add(DatasetAsset(id=asset['id'],title=asset['title'],category=asset['category'],source_url=asset['source_url'],license=asset['license'],
                    attribution=asset['attribution'],object_key=key,sha256=asset['sha256'],annotations=asset['annotations']));db.flush()
            else:
                existing=db.get(DatasetAsset,asset['id'])
                if existing.sha256==asset['sha256']:existing.attribution=asset['attribution']
            cid='showcase-'+asset['id']
            if db.get(Candidate,cid):continue
            helmet=asset['category']=='helmet_safety';labels=asset['annotations'].get('labels',[])
            bare=sum(a['label']=='Without Helmet' for a in labels);wearing=sum(a['label']=='With Helmet' for a in labels)
            negative=helmet and bare==0
            user=other if i%4==3 else primary
            number=('GJ00DM2010' if user.id==other.id else 'GJ00DM1010') if helmet else ('GJ00DM2001' if user.id==other.id else 'GJ00DM1001')
            status='REJECTED' if negative else 'CONFIRMED' if i%3!=0 else 'PENDING'
            rule='Helmet Violation' if helmet else 'restricted_zone'
            stamp=(datetime.now(timezone.utc)-timedelta(days=(i*2)%25,hours=i%7)).isoformat()
            desc=(f'The published dataset annotates {bare} head(s) without a helmet and {wearing} with a helmet. ' if helmet else 'A prerecorded traffic frame supports a hypothetical restricted-zone review exercise. ')
            desc+='This practice case uses a fictional registration and owner; it does not identify or accuse anyone in the source image.'
            c=Candidate(id=cid,event_key=cid,rule=rule,plate=number,location=['Ahmedabad · Demo junction','Gandhinagar · Demo corridor','Vadodara · Demo road'][i%3],
                status=status,created_at=stamp,model_version='dataset-annotation-example',explanation=desc,
                observations={'mode':'DATASET_DEMONSTRATION','published_annotations':asset['annotations'],'fictional_owner_assignment':True,'not_model_prediction':True},
                evidence=[{'key':key,'sha256':asset['sha256'],'content_type':'image/jpeg'}],
                reviewer=reviewer.id if status in ('CONFIRMED','REJECTED') else None,
                review_reason='Dataset shows helmeted heads; this negative practice case is rejected.' if negative else 'Demonstration review of published source annotations; owner link is fictional.' if status=='CONFIRMED' else None)
            db.add(c);db.flush();db.add(CaseMetadata(id=cid,is_demo=1,asset_id=asset['id'],note='Fictional test owner; attributed dataset imagery'))
            db.add(Audit(actor='local-showcase',action='DATASET_EVIDENCE_RECORDED',target=cid,created_at=stamp,details={'note':'Source imagery and annotation imported for a fictional practice case'}))
            if status in ('CONFIRMED','REJECTED'):db.add(Audit(actor=reviewer.id,action='REVIEW_'+status,target=cid,created_at=stamp,details={'reason':c.review_reason}))
            if status=='CONFIRMED':
                v=Violation(id='v-'+cid,candidate_id=cid,plate=number,rule=rule,location=c.location,created_at=stamp);db.add(v);db.flush()
                amount=100 if helmet else 500;state='SANDBOX_PAID' if i%2 else 'UNPAID'
                m=Memo(id='m-'+cid,violation_id=v.id,fine_amount=amount,status=state,created_at=stamp);db.add(m);db.flush()
                db.add(Audit(actor=reviewer.id,action='ISSUE_PROJECT_MEMO',target=m.id,created_at=stamp,details={'note':'Fictional showcase memo issued after a demonstration review'}))
                if state=='SANDBOX_PAID':
                    db.add(Payment(id='p-'+cid,memo_id=m.id,user_id=user.id,amount=amount,created_at=stamp));m.payment_date=stamp
                    db.add(Audit(actor=user.id,action='SANDBOX_PAYMENT',target=m.id,created_at=stamp,details={'note':'Demonstration receipt; no money transferred'}))
                db.add(Outbox(memo_id=m.id,recipient=user.email,status='PREVIEW',body='DATASET DEMONSTRATION MEMO\nFictional owner and registration. No actual enforcement notice.',created_at=stamp))
    engine.dispose();print('Loaded dataset assets, fictional vehicle profiles and linked case workflows without replacing existing records.')
if __name__=='__main__':main()
