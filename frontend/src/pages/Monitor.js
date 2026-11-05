import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import API_BASE, { http, errorMessage } from '../utils/api';
import { useResource, Status } from '../components/WorkspaceUI';

function ProcessedFrame({ session, sequence }) {
  const [frame, setFrame] = useState(null);
  useEffect(() => { if (!session || sequence == null) return;
    let active = true; let blobURL;
    http.get(`/api/operator/sessions/${session}/preview`, { responseType: 'blob' }).then(r => { blobURL = URL.createObjectURL(r.data); if (active) setFrame({session,sequence,url:blobURL}); }).catch(() => {});
    return () => { active = false; if (blobURL) URL.revokeObjectURL(blobURL); };
  }, [session, sequence]);
  return frame?.session===session && frame.sequence===sequence ? <img src={frame.url} alt="Analyzed source frame with aligned boxes, track IDs and source timestamp" /> : <div className="video-empty">{session?'Waiting for a processed frame…':'Start a source to see the analysed video here.'}</div>;
}
export default function Monitor() {
  const cameras = useResource('/api/operator/cameras'); const health = useResource('/api/operator/health', 5000);
  const [camera, setCamera] = useState(''); const [kind, setKind] = useState('webcam'); const [devices, setDevices] = useState([]); const [device, setDevice] = useState('');
  const [session, setSession] = useState(''); const status = useResource(session ? `/api/operator/sessions/${session}` : null, 1000);
  const events = useResource(session ? `/api/operator/candidates?session_id=${session}&size=10` : null, 3000);
  const jobs = useResource('/api/operator/jobs', 3000); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [file, setFile] = useState(null); const [fileURL, setFileURL] = useState(''); const [progress, setProgress] = useState(0);
  const [storedURL, setStoredURL] = useState('');
  useEffect(() => () => { if (storedURL) URL.revokeObjectURL(storedURL); }, [storedURL]);
  const [signal, setSignal] = useState('unknown'); const signalRef = useRef({ state: 'unknown', timestamp: 0 });
  const video = useRef(null); const stream = useRef(null); const timer = useRef(null); const sessionRef = useRef(''); const startTime = useRef(0); const seq = useRef(0); const inFlight = useRef(false); const skipped = useRef(0);
  const [clientDrops, setClientDrops] = useState(0);
  function cleanup() { clearInterval(timer.current); timer.current = null; stream.current?.getTracks().forEach(t => t.stop()); stream.current = null; if (video.current) video.current.srcObject = null; }
  useEffect(() => () => { cleanup(); if (sessionRef.current) http.post(`/api/operator/sessions/${sessionRef.current}/stop`).catch(() => {}); }, []);
  useEffect(() => { if (status.data && status.data.id === session && status.data.status !== 'RUNNING') cleanup(); }, [status.data, session]);
  useEffect(() => { if (!file) { setFileURL(''); return; } const url = URL.createObjectURL(file); setFileURL(url); return () => URL.revokeObjectURL(url); }, [file]);
  async function discover() {
    try {
      if (!navigator.mediaDevices) throw new Error('Camera access requires HTTPS or localhost.');
      const permission = await navigator.mediaDevices.getUserMedia({ video: true, audio: false }); permission.getTracks().forEach(t => t.stop());
      setDevices((await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'videoinput'));
    } catch (e) { setError(`Camera permission/device unavailable: ${e.message}`); }
  }
  async function transmit() {
    if (inFlight.current || !video.current?.videoWidth) { skipped.current++; setClientDrops(skipped.current); return; }
    if(video.current.videoWidth<100||video.current.videoHeight<100){
      skipped.current++;setClientDrops(skipped.current);
      if(performance.now()-startTime.current>8000){setError('The camera did not supply a usable video frame. Select another device or retry after closing other camera applications.');await stop();}
      return;
    }
    inFlight.current = true;
    try {
      const canvas = document.createElement('canvas'); const v = video.current; const scale = Math.min(1, 1280 / Math.max(v.videoWidth, v.videoHeight));
      canvas.width = Math.round(v.videoWidth * scale); canvas.height = Math.round(v.videoHeight * scale); canvas.getContext('2d').drawImage(v, 0, 0, canvas.width, canvas.height);
      const timestamp = (performance.now() - startTime.current) / 1000; const frameSeq = seq.current++;
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .78));
      const headers = { 'Content-Type': 'image/jpeg', 'X-Sequence': frameSeq, 'X-Source-Time': timestamp };
      if (signalRef.current.state !== 'unknown') { headers['X-Signal-State'] = signalRef.current.state; headers['X-Signal-Time'] = signalRef.current.timestamp; }
      await http.post(`/api/operator/sessions/${sessionRef.current}/frames`, blob, { headers });
    } catch (e) { setError(errorMessage(e)); } finally { inFlight.current = false; }
  }
  async function start() {
    setError(''); setBusy(true); cleanup();
    try {
      if (kind === 'webcam') {
        if (!navigator.mediaDevices) throw new Error('Camera access requires HTTPS or localhost.');
        stream.current = await navigator.mediaDevices.getUserMedia({ video: device ? { deviceId: { exact: device }, width: { ideal: 1280 } } : { width: { ideal: 1280 } }, audio: false });
        video.current.srcObject = stream.current; await video.current.play();
      }
      const res = await http.post('/api/operator/sessions', { camera_id: camera, kind });
      sessionRef.current = res.data.id; setSession(res.data.id); startTime.current = performance.now(); seq.current = 0; skipped.current=0;setClientDrops(0);signalRef.current = { state: 'unknown', timestamp: 0 }; setSignal('unknown');
      if (kind === 'webcam') timer.current = setInterval(transmit, 1000);
    } catch (e) { cleanup(); setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function stop() {
    cleanup(); try { if (sessionRef.current) await http.post(`/api/operator/sessions/${sessionRef.current}/stop`); status.reload(); } catch (e) { setError(errorMessage(e)); } sessionRef.current = '';
  }
  async function upload(e) {
    e.preventDefault(); setBusy(true); setError(''); setProgress(0);
    try {
      if (!file || file.size > 100 * 1024 * 1024) throw new Error('Choose a video no larger than 100 MiB.');
      const ticket = (await http.post('/api/operator/uploads', { camera_id: camera, filename: file.name, size: file.size, content_type: file.type })).data;
      const url = ticket.upload_url.startsWith('/') ? API_BASE + ticket.upload_url : ticket.upload_url;
      // The scoped upload URL has its own authorization. Never send the application JWT to storage.
      await axios({ url, method: ticket.method, data: file, headers: ticket.headers, timeout: 300000, onUploadProgress: p => setProgress(Math.round(100 * p.loaded / file.size)) });
      await http.post(`/api/operator/jobs/${ticket.job_id}/submit`); setSession(ticket.session_id); jobs.reload();
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }
  async function loadOriginal(jobId,sessionId) {
    const r=await http.get(`/api/operator/jobs/${jobId}/source`,{responseType:'blob'});let blob=r.data;
    if(blob.type.includes('json')){const value=JSON.parse(await blob.text());blob=(await axios.get(value.signed_url,{responseType:'blob'})).data;}
    setFile(null);setKind('upload');setStoredURL(URL.createObjectURL(blob));setSession(sessionId);
  }
  async function sample(){setBusy(true);setError('');try{cleanup();const r=await http.post('/api/samples/rush-hour/run',{});setStoredURL('');setFile(null);setKind('upload');setCamera('demo-camera');setSession(r.data.session_id);jobs.reload();await loadOriginal(r.data.job_id,r.data.session_id);}catch(e){setError(errorMessage(e));}finally{setBusy(false);}}

  const running = status.data?.id === session && status.data?.status === 'RUNNING'; const metrics = status.data?.result || {};
  return <div className="workspace"><header className="page-heading"><span className="eyebrow">TRAFFIC VIDEO ANALYSIS</span><h1>Live traffic monitoring</h1><p>Detect and track vehicles, inspect possible rule breaches, and send evidence for RTO review.</p><Link to="/calibration">Camera setup →</Link></header>
    <section className="overview-intro"><div><span className="eyebrow">START WITH THE INCLUDED EXAMPLE</span><h2>See real vehicle analysis without setting up a camera.</h2><p>The 20-second prerecorded traffic clip runs through detection, tracking, evidence capture and a deliberately configured practice zone. It usually takes about 30 seconds on this computer.</p></div><div className="intro-action"><button disabled={busy||running||!health.data?.model_ready} onClick={sample}>Analyse included traffic video</button><small>CC0 source footage · practice zone · human review required</small></div></section>
    <div className="panel source-toolbar"><label>Camera / calibration<select value={camera} disabled={running} onChange={e => setCamera(e.target.value)}><option value="">Select a camera</option>{cameras.data?.map(c => <option key={c.id} value={c.id}>{c.name} · v{c.version}</option>)}</select></label>
      <label>Video source<select value={kind} disabled={running} onChange={e => { setKind(e.target.value); setSession(''); }}><option value="webcam">Browser webcam — live</option><option value="upload">Uploaded video — prerecorded</option></select></label>
      <span className={`badge ${health.data?.model_ready ? 'good' : ''}`}>{health.data?.model_ready ? 'Detection ready' : 'Start the analysis service'}</span>
    </div>
    {error && <p role="alert" className="notice danger">{error}</p>}{cameras.error && <p className="danger">{cameras.error}</p>}
    {kind === 'webcam' && <div className="panel actions"><button disabled={running} onClick={discover}>Find / allow cameras</button><label>Camera device<select disabled={running} value={device} onChange={e => setDevice(e.target.value)}><option value="">Default camera</option>{devices.map(d => <option value={d.deviceId} key={d.deviceId}>{d.label || 'Camera'}</option>)}</select></label></div>}
    {kind === 'webcam' ? <div className="actions"><button disabled={busy || running || !camera || !health.data?.model_ready} onClick={start}>Start {kind === 'webcam' ? 'webcam' : 'configured stream'}</button><button disabled={!running} onClick={stop}>Stop & release camera</button></div>
      : <form className="panel actions" onSubmit={upload}><label>Choose prerecorded video (≤100 MiB, ≤10 minutes)<input type="file" accept="video/mp4,video/webm,video/quicktime,video/x-msvideo" onChange={e => { setFile(e.target.files[0]); setStoredURL(''); }} /></label><button disabled={busy || !camera || !file}>Upload & queue processing</button><progress max="100" value={progress} aria-label="Upload progress" /><span>{progress}%</span><p>Upload a clear, fixed-view video. Review the result before confirming a case.</p></form>}
    <div className="two-columns"><section className="panel"><h2>{kind === 'upload' ? 'Prerecorded source / seek preview' : kind === 'webcam' ? 'Live input preview' : 'Configured gateway source'}</h2>
      {kind === 'webcam' ? <video className="source-video" ref={video} autoPlay playsInline muted /> : kind === 'upload' ? <video className="source-video" ref={video} controls src={storedURL || (file?fileURL:undefined)} /> : <p>RTSP(S) is decoded by the Python worker. The analyzed preview is browser-compatible JPEG.</p>}
      {kind === 'webcam' && <label>MANUAL signal observation<select value={signal} onChange={e => { setSignal(e.target.value); signalRef.current = { state: e.target.value, timestamp: Math.max(0, (performance.now() - startTime.current) / 1000) }; }}><option value="unknown">Unknown — red-light rule cannot trigger</option><option value="red">Manual RED observation</option><option value="green">Manual GREEN observation</option></select><small>Observation expires after the configured maximum age. Reselect a state to refresh its timestamp.</small></label>}
    </section><section className="panel"><h2>Analyzed frame · {status.data?.status || 'Idle'}</h2><ProcessedFrame session={session} sequence={metrics.sequence} /><p className="muted">Boxes belong to the timestamped analyzed frame shown here. Live input may be ahead.</p>
      <div className="metrics">{[['Input FPS', metrics.source_fps?.toFixed(2)],['Inference FPS', metrics.inference_fps],['Inference latency', metrics.latency_ms == null ? null : `${metrics.latency_ms} ms`],['Worker drops', status.data?.dropped],['Client skips', clientDrops],['Source time', metrics.source_time == null ? null : `${metrics.source_time.toFixed(2)}s`]].map(([name, value]) => <div key={name}><small>{name}</small><strong>{value ?? '—'}</strong></div>)}</div><p className="danger">{metrics.error}</p></section></div>
    <div className="two-columns"><section className="panel"><h2>Recent candidates</h2>{events.data?.items.map(c => <article key={c.id}><Link to={`/cases/${c.id}`}>{c.rule} · track {c.track_id}</Link><p>{c.explanation}</p>{kind === 'upload' && c.source_time != null && <button onClick={() => { if (video.current) video.current.currentTime = c.source_time; }}>Seek to {c.source_time.toFixed(2)}s</button>}</article>)}{!events.data?.items.length && <p>No candidate events for this source. Object detection alone is not a violation.</p>}</section>
      <section className="panel"><h2>What this camera can evaluate</h2><p>This project detects vehicles and flags configured movement rules for review. The RTO checks the evidence and plate before issuing a memo.</p><details><summary>Camera rule settings</summary>{cameras.data?.find(c => c.id === camera)?.capabilities.filter(c => ['wrong_way','restricted_zone','red_light','speeding','no_parking','stop_line'].includes(c.rule)).map(c => <p key={c.rule}><span className={`badge ${c.enabled ? 'good' : ''}`}>{c.enabled ? 'ENABLED' : 'DISABLED'}</span> <strong>{c.rule.replaceAll('_', ' ')}</strong> — {c.reason}</p>)}</details></section></div>
    <section className="panel"><h2>Video processing history</h2><Status {...jobs}>{jobs.data?.items.map(j => <div className="job-row" key={j.id} data-job-id={j.id}><div><strong>{j.kind} · {j.status}</strong><p>{j.error || `${Math.round(j.progress * 100)}% processed`}</p></div><button disabled={busy} onClick={async () => { setBusy(true);try { await loadOriginal(j.id,j.session_id); } catch(e) { setError(errorMessage(e)); } finally { setBusy(false); } }}>View results</button>{['QUEUED','RUNNING','AWAITING_UPLOAD'].includes(j.status) && <button onClick={async () => { try { await http.post(`/api/operator/jobs/${j.id}/cancel`); jobs.reload(); } catch (e) { setError(errorMessage(e)); } }}>Cancel</button>}</div>)}</Status></section>
    <p className="muted">Videos are processed one at a time. Webcam frames are sampled once per second and uploaded videos approximately twice per second. Sampling can miss events; every flagged event requires human review.</p>
  </div>;
}
