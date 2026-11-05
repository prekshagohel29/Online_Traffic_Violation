import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { http, errorMessage, download, localTime } from '../utils/api';
export function useResource(path, interval = 0) {
  const [result, setResult] = useState({path:null,data:null}); const [error, setError] = useState(''); const [version, setVersion] = useState(0);
  useEffect(() => {
    let alive = true; let timer;const controller=new AbortController();setError('');
    async function load() {
      try { const res = await http.get(path,{signal:controller.signal}); if (alive) { setResult({path,data:res.data}); setError(''); } }
      catch (e) { if (alive && e.code!=='ERR_CANCELED') setError(errorMessage(e)); }
      if (alive && interval) timer = setTimeout(load, interval);
    }
    if (path) load(); return () => { alive = false; clearTimeout(timer);controller.abort(); };
  }, [path, interval, version]);
  return { data:result.path===path?result.data:null, error, reload: () => setVersion(v => v + 1) };
}
export function Status({ error, data, children }) {
  if (error) return <p className="notice danger" role="alert">{error}</p>;
  if (!data) return <p role="status">Loading…</p>;
  return children;
}
export function Pager({ page, setPage, total, size = 25 }) {
  return <div className="pager"><button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page} · {total || 0} records</span><button disabled={page * size >= total} onClick={() => setPage(page + 1)}>Next</button></div>;
}
export function MemoCard({ memo: m, citizen, reload }) {
  const [reason, setReason] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function act(kind) {
    setBusy(true); setError('');
    try {
      if (kind === 'pay') await http.post('/api/user/pay', { memo_id: m.id, mode: 'SANDBOX', acknowledge_no_money: true });
      else await http.post('/api/user/disputes', { memo_id: m.id, reason });
      setReason(''); reload();
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <article className="panel memo-row"><div><span className="eyebrow">PROJECT MEMO · {m.id.slice(0, 8)}</span><h3>{m.violation_type.replaceAll('_', ' ')}</h3>
    <p><strong>{m.plate || 'Unknown / unreadable plate'}</strong> · {m.location}</p><p className="muted">{localTime(m.date_time)} IST</p>
    {m.source_time != null && <p>Source timeline: {m.source_time.toFixed(2)} seconds</p>}
    <span className="badge">{m.status.replaceAll('_', ' ')}</span>
    {m.candidate_id && <Link to={`/cases/${m.candidate_id}`}>View complete case & evidence →</Link>}
    {m.payment && <p>Sandbox receipt: {m.payment.id} · No money transferred.</p>}
    {m.dispute && <p>Dispute {m.dispute.status}: {m.dispute.decision || m.dispute.reason}</p>}
    {citizen && m.dispute?.status === 'PENDING' && <label>Add supporting dispute image (JPEG/PNG, ≤2 MiB)<input type="file" accept="image/jpeg,image/png" onChange={async e => { const file=e.target.files[0]; if (!file) return; try { await http.post(`/api/disputes/${m.dispute.id}/evidence`,file,{headers:{'Content-Type':file.type}}); reload(); } catch(err) { setError(errorMessage(err)); } }} /><small>{m.dispute.evidence.length} supporting image(s) attached</small></label>}
    <p className="muted">{m.policy_label}</p></div>
    <div className="memo-controls"><strong className="amount">₹{m.fine_amount.toLocaleString('en-IN')}</strong>
      <button onClick={() => download(`/api/memos/${m.id}/pdf`, `project-memo-${m.id}.pdf`).catch(e => setError(errorMessage(e)))}>Download memo / receipt</button>
      {citizen && m.status === 'UNPAID' && <><p className="muted">Sandbox only. This transfers no real money.</p><button disabled={busy} onClick={() => act('pay')}>Record sandbox payment</button>
      {!m.dispute && <form onSubmit={e => { e.preventDefault(); act('dispute'); }}><label>Dispute explanation<textarea required minLength={5} maxLength={3000} value={reason} onChange={e => setReason(e.target.value)} /></label><button disabled={busy}>Submit dispute</button></form>}</>}
      {error && <p role="alert" className="danger">{error}</p>}
    </div></article>;
}
