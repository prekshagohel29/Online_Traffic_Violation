import React, { useState } from 'react';
import { Link,useSearchParams } from 'react-router-dom';
import { useResource, Status, Pager, MemoCard } from '../components/WorkspaceUI';
import { http, errorMessage, download, localTime } from '../utils/api';
import { PrivateImage } from './Evidence';
import { Badge,labels,ruleName } from '../components/ExperienceUI';

function Ownership() {
  const [page, setPage] = useState(1); const rows = useResource(`/api/operator/ownership?page=${page}`);
  const [reasons, setReasons] = useState({}); const [checked, setChecked] = useState({}); const [error, setError] = useState('');
  async function decide(id, decision) {
    try { await http.post(`/api/operator/ownership/${id}/review`, { decision, reason: reasons[id], proof_checked: checked[id] === true }); rows.reload(); }
    catch (e) { setError(errorMessage(e)); }
  }
  return <><h2>Ownership verification</h2>{error && <p role="alert" className="notice danger">{error}</p>}<Status {...rows}>{rows.data?.items.map(r => <article className="panel" key={r.id}>
    <h3>{r.plate} <Badge value={r.status}/></h3><p>Applicant: {r.applicant}</p><p>Proof reference: {r.proof}</p>
    {r.status === 'PENDING' ? <><label>Verification / rejection reason<textarea value={reasons[r.id] || ''} onChange={e => setReasons({ ...reasons, [r.id]: e.target.value })} /></label>
    <label className="check"><input type="checkbox" checked={!!checked[r.id]} onChange={e => setChecked({ ...checked, [r.id]: e.target.checked })} />I checked the registration document and applicant identity outside this project.</label>
    <div className="actions"><button disabled={!checked[r.id] || !reasons[r.id]} onClick={() => decide(r.id, 'APPROVED')}>Approve ownership</button><button disabled={!reasons[r.id]} onClick={() => decide(r.id, 'REJECTED')}>Reject request</button></div></> : <p>{r.reason}</p>}
  </article>)}<Pager page={page} setPage={setPage} total={rows.data?.total} /></Status></>;
}
function Manual() {
  const [d, setD] = useState({ plate: '', type: 'Signal Jump', location: '', explanation: '' });
  const [message, setMessage] = useState(''); const [created, setCreated] = useState(null); const [busy, setBusy] = useState(false);
  const [key, setKey] = useState(() => crypto.randomUUID());
  async function submit(e) {
    e.preventDefault(); setBusy(true);
    try { const res = await http.post('/api/operator/manual', d, { headers: { 'Idempotency-Key': key } }); setCreated(res.data); setMessage('Candidate saved for review. Attach evidence before confirmation.'); setKey(crypto.randomUUID()); }
    catch (err) { setMessage(errorMessage(err)); } finally { setBusy(false); }
  }
  return <div className="panel"><h2>Manual candidate entry</h2><p>Manual observations enter the review queue. Video cannot establish intoxication, missing licences or actual load weight.</p>
    <form onSubmit={submit} className="form-grid"><label>Plate (optional if unreadable)<input value={d.plate} maxLength={25} onChange={e => setD({ ...d, plate: e.target.value.toUpperCase() })} /></label>
      <label>Violation type<select value={d.type} onChange={e => setD({ ...d, type: e.target.value })}>{['Signal Jump','Helmet Violation','Speeding','Parking Violation','No License','Overloading','Drunk Driving','wrong_way','restricted_zone'].map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Location<input required maxLength={150} value={d.location} onChange={e => setD({ ...d, location: e.target.value })} /></label>
      <label>Observed facts and evidence reference<textarea required maxLength={3000} value={d.explanation} onChange={e => setD({ ...d, explanation: e.target.value })} /></label><button disabled={busy}>Submit for review</button></form>
    <p role="status">{message}</p>{created && <Link to={`/cases/${created.id}`}>Open candidate and attach evidence →</Link>}
  </div>;
}
function Disputes() {
  const rows = useResource('/api/operator/disputes'); const [reason, setReason] = useState({}); const [error, setError] = useState('');
  async function decide(id, decision) { try { await http.post(`/api/operator/disputes/${id}/review`, { decision, reason: reason[id] }); rows.reload(); } catch (e) { setError(errorMessage(e)); } }
  return <><h2>Citizen disputes</h2><p className="danger" role="alert">{error}</p><Status {...rows}>{rows.data?.items.length === 0 && <div className="panel empty">No disputes.</div>}{rows.data?.items.map(r => <div className="panel" key={r.id}><h3>{r.memo_id} · {r.status}</h3><p>{r.reason}</p>
    {r.evidence.map((item,i)=><PrivateImage key={item.key} path={`/api/disputes/${r.id}/evidence/${i}`} alt="Citizen supporting dispute evidence" />)}
    {r.status === 'PENDING' && <><label>Decision reason<textarea value={reason[r.id] || ''} onChange={e => setReason({ ...reason, [r.id]: e.target.value })} /></label><div className="actions"><button disabled={!reason[r.id]} onClick={() => decide(r.id, 'UPHELD')}>Uphold dispute / void memo</button><button disabled={!reason[r.id]} onClick={() => decide(r.id, 'DISMISSED')}>Dismiss / restore unpaid</button></div></>}{r.decision && <p>{r.decision}</p>}</div>)}</Status></>;
}
export default function RTODashboard() {
  const [params,setParams]=useSearchParams();
  const tab=params.get('tab')||'Review queue';const setTab=value=>setParams({tab:value}); const [page, setPage] = useState(1); const [filter, setFilter] = useState('PENDING');
  const queue = useResource(`/api/operator/candidates?status=${filter}&page=${page}`, 5000);
  const memos = useResource(`/api/operator/memos?page=${page}`); const notices = useResource('/api/operator/notifications');
  const [error, setError] = useState('');
  return <div className="workspace theme-rto"><header className="page-heading"><span className="eyebrow">RTO OPERATIONS</span><h1>RTO Control Center</h1><p>Inspect evidence. Record decisions. Issue traceable project memos.</p><Link className="primary-link" to="/monitor">Open live monitoring →</Link></header>
    <div className="tabbar" role="tablist" aria-label="RTO workflows">{['Review queue','Manual entry','Ownership','Memos','Disputes','Notifications'].map(t => <button key={t} role="tab" aria-selected={tab === t} onClick={() => { setTab(t); setPage(1); }}>{t}</button>)}</div>
    {tab === 'Review queue' && <><div className="section-heading"><h2>Candidate review queue</h2><label>Status<select value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}>{['PENDING','NEEDS_EVIDENCE','CONFIRMED','REJECTED'].map(s => <option key={s} value={s}>{labels[s]||s}</option>)}</select></label></div>
    <Status {...queue}>{queue.data?.items.length === 0 && <div className="panel empty">No candidates in this state. Start a calibrated source or submit a manual observation.</div>}
      {queue.data?.items.map(c => <article className="panel candidate-row" key={c.id}><div><Badge value={c.status}/><h3>{ruleName(c.rule)}</h3><p>{c.location} · Track {c.track_id ?? 'manual'} · {c.plate || 'Unreadable / not reviewed'}</p><p>{c.explanation}</p><small>{c.source_time != null ? `${c.source_time.toFixed(2)}s source timeline` : localTime(c.created_at)} · {c.evidence.length} evidence item(s)</small></div><Link to={`/cases/${c.id}`}>Inspect & review →</Link></article>)}
    <Pager page={page} setPage={setPage} total={queue.data?.total} /></Status></>}
    {tab === 'Manual entry' && <Manual />}{tab === 'Ownership' && <Ownership />}{tab === 'Disputes' && <Disputes />}
    {tab === 'Memos' && <><div className="section-heading"><h2>Issued project memos</h2><button onClick={() => download('/api/operator/export', 'project-memos.csv').catch(e => setError(errorMessage(e)))}>Export CSV (up to 10,000)</button></div><p className="danger">{error}</p><Status {...memos}>{memos.data?.items.map(m => <MemoCard key={m.id} memo={m} reload={memos.reload} />)}<Pager page={page} setPage={setPage} total={memos.data?.total} /></Status></>}
    {tab === 'Notifications' && <><h2>Owner notice previews</h2><p>These saved notices demonstrate what a verified vehicle owner would receive. Preview notices do not send email.</p><Status {...notices}>{notices.data?.items.length === 0 && <div className="panel empty">No notifications queued. Unknown owners never receive a guessed notice.</div>}{notices.data?.items.map(n => <article className="panel" key={n.id}><span className="badge">{n.status}</span><p>{n.recipient} · {n.attempts} attempt(s)</p><pre>{n.body}</pre><p>{n.error}</p></article>)}</Status></>}
  </div>;
}
