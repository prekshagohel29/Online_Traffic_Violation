import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { configurationError } from '../utils/api';
import './Auth.css';
export default function Auth() {
  const selected = new URLSearchParams(useLocation().search).get('role');
  const role = ['USER','RTO','GOVT','ADMIN'].includes(selected) ? selected : 'USER';
  const [signup, setSignup] = useState(false); const [email, setEmail] = useState('');
  const [password, setPassword] = useState(''); const [name, setName] = useState('');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const auth = useAuth(); const navigate = useNavigate();
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    const result = signup ? await auth.register(email, password, name, 'USER') : await auth.login(email, password);
    setBusy(false); if (result.success) navigate('/'); else setError(result.message);
  }
  return <div className={`auth-container theme-${role.toLowerCase()}`}>
    <button className="back-btn" onClick={() => navigate('/')}>← Change portal</button>
    <div className="auth-card"><div className="auth-header"><div className="role-badge">{role} PORTAL</div>
      <h2>{signup ? 'Create your account' : 'Welcome back'}</h2><p>e-Memo traffic management project</p></div>
      {role === 'USER' && <div className="tabs"><button className={`tab ${!signup ? 'active' : ''}`} onClick={() => setSignup(false)}>Login</button><button className={`tab ${signup ? 'active' : ''}`} onClick={() => setSignup(true)}>Sign up</button></div>}
      {(error || configurationError) && <p className="notice danger" role="alert">{error || configurationError}</p>}
      <form className="auth-form" onSubmit={submit}>
        {signup && <label>Full name<input value={name} onChange={e => setName(e.target.value)} required maxLength={150} autoComplete="name" /></label>}
        <label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" /></label>
        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={signup ? 10 : 1} maxLength={200} autoComplete={signup ? 'new-password' : 'current-password'} /></label>
        {signup && <p className="muted">Use at least 10 characters. Vehicle ownership is verified separately after signup.</p>}
        <button className="submit-btn" disabled={busy || !!configurationError}>{busy ? 'Please wait…' : signup ? 'Create citizen account' : 'Login'}</button>
      </form>
      <p className="muted">Need help accessing your account? Contact your project administrator.</p>
      {role !== 'USER' && <p className="notice">Staff accounts are provisioned by a trusted administrator.</p>}
    </div></div>;
}
