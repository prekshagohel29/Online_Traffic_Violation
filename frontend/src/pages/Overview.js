import React,{useState} from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useResource,Status } from '../components/WorkspaceUI';
import { PageHeader,Stats,CaseList,Workflow,ScopeControl,HelpNote,money } from '../components/ExperienceUI';
export default function Overview(){
  const {user}=useAuth();const [scope,setScope]=useState('all');const stats=useResource('/api/overview?scope='+scope,5000);const data=stats.data;
  return <div className="workspace"><PageHeader eyebrow="RTO WORKSPACE" title="Traffic operations, at a glance" description={`Welcome, ${user.full_name}. Review the evidence, make a decision, and follow each case through to resolution.`}><Link className="primary-link" to="/cases?status=PENDING">Review pending cases →</Link></PageHeader>
  <div className="overview-intro"><div><span className="eyebrow">START HERE</span><h2>One case. A clear path from evidence to resolution.</h2><p>Every record stays connected: vehicle, owner, evidence, RTO decision, memo and citizen response.</p><Workflow current={0}/></div><Link className="intro-action" to="/datasets"><span>Explore a ready-made example</span><strong>Open dataset examples →</strong><small>Real source imagery · fictional demonstration identities</small></Link></div>
  <div className="section-heading"><h2>Today’s workspace</h2><ScopeControl value={scope} onChange={setScope}/></div><Status {...stats}>
  <Stats items={[["Awaiting review",data?.pending,'Evidence awaiting an RTO decision','amber'],['Confirmed cases',data?.confirmed,'Reviewed and recorded','blue'],['Open disputes',data?.disputes,'Citizen responses to resolve','red'],['Outstanding memos',money(data?.money.UNPAID),'Project demo fine policy','green']]}/>
  <div className="quick-grid"><Link to="/monitor"><span>01</span><strong>Analyse traffic footage</strong><p>Use the included clip, upload footage, or start a browser webcam.</p></Link><Link to="/operations?tab=Ownership"><span>02</span><strong>Verify a vehicle owner</strong><p>Check a pending ownership request before citizen access.</p></Link><Link to="/operations?tab=Disputes"><span>03</span><strong>Resolve a dispute</strong><p>Review a citizen’s explanation and supporting evidence.</p></Link></div>
  <section className="panel"><div className="section-heading"><div><span className="eyebrow">CASE REGISTER</span><h2>Recent cases</h2></div><Link to="/cases">View all {data?.total} cases →</Link></div><CaseList items={data?.recent}/></section>
  <HelpNote>{data?.demos||0} records in this view are demonstration examples. Their imagery is attributed, and their owner links are fictional. Use the source selector to explore examples separately.</HelpNote>
  </Status></div>;
}
