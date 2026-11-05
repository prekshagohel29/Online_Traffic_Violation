import React, { createContext, useState, useEffect, useContext } from 'react';
import { http, errorMessage } from '../utils/api';
const Context = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); const [loading, setLoading] = useState(true);
  useEffect(() => {
    // Discard old stored roles and tokens from the previous implementation.
    localStorage.removeItem('token'); localStorage.removeItem('user'); sessionStorage.removeItem('user');
    const expired = () => setUser(null); window.addEventListener('session-expired', expired);
    const load = async () => {
      try { if (sessionStorage.getItem('token')) setUser((await http.get('/api/auth/me')).data); }
      catch { sessionStorage.removeItem('token'); } finally { setLoading(false); }
    };
    load(); return () => window.removeEventListener('session-expired', expired);
  }, []);
  const authenticate = async (path, data) => {
    try {
      const res = await http.post(path, data); sessionStorage.setItem('token', res.data.access_token);
      setUser(res.data.user); return { success: true };
    } catch (e) { return { success: false, message: errorMessage(e) }; }
  };
  const login = (email, password) => authenticate('/api/auth/login', { email, password });
  const register = (email, password, full_name, role, details = {}) => authenticate('/api/auth/register', { email, password, full_name, role: 'USER', ...details });
  const logout = async () => {
    try { await http.post('/api/auth/logout'); } catch {} finally { sessionStorage.removeItem('token'); setUser(null); }
  };
  const updateProfile = async data => {
    try {
      await http.put('/api/user/profile', data);
      if (data.password) await logout(); else setUser((await http.get('/api/auth/me')).data);
      return { success: true };
    } catch (e) { return { success: false, message: errorMessage(e) }; }
  };
  return <Context.Provider value={{ user, loading, login, register, logout, updateProfile }}>{loading ? <p role="status">Checking your session…</p> : children}</Context.Provider>;
}
export const useAuth = () => useContext(Context);
