import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useResource, Status } from '../components/WorkspaceUI';
import { http, errorMessage, localTime } from '../utils/api';
export function PrivateImage({ path, alt }) {
  const [url, setUrl] = useState(''); const [error, setError] = useState('');
  useEffect(() => { let active = true; let objectURL;
    http.get(path, { responseType: 'blob' }).then(r => { objectURL = URL.createObjectURL(r.data); if (active) setUrl(objectURL); }).catch(() => { if (active) setError('Evidence missing, expired or unavailable.'); });
    return () => { active = false; if (objectURL) URL.revokeObjectURL(objectURL); };
  }, [path]);
  return error ? <p className="notice danger">{error}</p> : url ? <img className="evidence-image" src={url} alt={alt} /> : <p>Loading private evidence…</p>;
}
export default function Evidence() {
  const { id } = useParams(); const resource = useResource(`/api/candidates/${id}`); const { user } = useAuth();
  const staff = ['RTO','ADMIN'].includes(user.role); const [reason, setReason] = useState(''); const [plate, setPlate] = useState('');
  const [checked, setChecked] = useState(false); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const c = resource.data;
  async function decide(decision) {
    setBusy(true); try { await http.post(`/api/operator/candidates/${id}/review`, { decision, reason, plate: plate || c.plate || '', evidence_reviewed: checked }); setMessage('Decision saved.'); resource.reload(); }
    catch (e) { setMessage(errorMessage(e)); } finally { setBusy(false); }
  }
  async function attach(file) {
    if (!file) return; setBusy(true);
    try { await http.post(`/api/candidates/${id}/evidence`, file, { headers: { 'Content-Type': file.type } }); resource.reload(); }
    catch (e) { setMessage(errorMessage(e)); } finally { setBusy(false); }
  }
  return <div className="workspace"><Link to={staff ? '/rto' : '/dashboard'}>← Back to memos / review</Link><Status {...resource}>{c && <><header className="page-heading"><span className="eyebrow">EVIDENCE & REVIEW</span><h1>{c.rule.replaceAll('_', ' ')}</h1><span className="badge">{c.status}</span><p>{c.explanation}</p></header>
    <div className="two-columns"><section className="panel"><h2>Source evidence</h2><p>{c.location} · {c.source_time == null ? 'Manual event' : `Timeline ${c.source_time.toFixed(3)}s (absolute capture time unknown)`}</p><p>Processing time: {localTime(c.created_at)} IST</p>
    {c.evidence.length === 0 ? <p className="notice danger">No evidence attached. Confirmation is blocked.</p> : c.evidence.map((e, index) => <figure key={e.key}><PrivateImage path={`/api/candidates/${id}/evidence/${index}`} alt={index === 0 ? 'Timestamped candidate evidence snapshot' : 'Uncertain plate proposal crop'} /><figcaption>{index === 0 ? 'Evidence snapshot' : 'Plate proposal — requires review'} · SHA-256 {e.sha256}</figcaption></figure>)}
    <p className="muted">Short pre/post-event clips are not captured in this build. The uploaded source stays available to its operator.</p>
    {staff && ['PENDING','NEEDS_EVIDENCE'].includes(c.status) && <label>Attach JPEG or PNG evidence (maximum 2 MiB)<input disabled={busy} type="file" accept="image/jpeg,image/png" onChange={e => attach(e.target.files[0])} /></label>}
    </section><aside className="panel"><h2>Observation details</h2><dl><dt>Plate</dt><dd>{c.plate || 'Unreadable / unknown'}</dd><dt>Track</dt><dd>{c.track_id ?? 'Manual'}</dd><dt>Model</dt><dd>{c.model_version}</dd><dt>Rule version</dt><dd>{c.rule_version}</dd><dt>Calibration version</dt><dd>{c.calibration_version ?? 'Not applicable'}</dd></dl>
    <details><summary>Measurements, thresholds and source configuration</summary><pre>{JSON.stringify(c.observations, null, 2)}</pre></details><details><summary>Raw OCR observations</summary><pre>{JSON.stringify(c.raw_ocr, null, 2)}</pre><p>No reading is treated as verified ownership.</p></details>
    {staff && ['PENDING','NEEDS_EVIDENCE'].includes(c.status) && <><h2>Record a review decision</h2><label>Reviewed plate (leave blank if unreadable)<input value={plate} onChange={e => setPlate(e.target.value.toUpperCase())} maxLength={25} placeholder={c.plate || 'No guessed plates'} /></label><label>Decision reason<textarea value={reason} onChange={e => setReason(e.target.value)} maxLength={3000} /></label><label className="check"><input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} />I reviewed the evidence, rule context and plate uncertainty.</label>
    <div className="actions"><button disabled={busy || !checked || !reason || c.evidence.length === 0} onClick={() => decide('CONFIRMED')}>Confirm & issue project memo</button><button disabled={busy || !reason} onClick={() => decide('REJECTED')}>Reject</button><button disabled={busy || !reason} onClick={() => decide('NEEDS_EVIDENCE')}>Request more evidence</button></div></>}
    <p role="status">{message}</p>{c.review_reason && <p>Review reason: {c.review_reason}</p>}{staff && c.related_candidates?.length > 0 && <details><summary>Related camera/rule candidates — inspect for duplicates</summary>{c.related_candidates.map(x=><p key={x.id}><Link to={`/evidence/${x.id}`}>{x.id.slice(0,8)} · {x.status}</Link> · {x.source_time ?? 'unknown'}s · session {x.session_id?.slice(0,8)}</p>)}</details>}<details><summary>Review history</summary><pre>{JSON.stringify(c.history, null, 2)}</pre></details></aside></div>
  </>}</Status></div>;
}
