import axios from 'axios';
const configured = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/$/, '');
const API_BASE =
    configured ||
    (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');
export const configurationError =
    process.env.NODE_ENV === 'production' && !configured
        ? 'The API address has not been configured. Set REACT_APP_API_BASE_URL and rebuild the website.'
        : '';
export const http = axios.create({ baseURL: API_BASE, timeout: 20000 });
http.interceptors.request.use((config) => {
    const token = sessionStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});
http.interceptors.response.use(
    (r) => r,
    (error) => {
        if (
            error.response?.status === 401 &&
            !error.config?.url?.includes('/auth/login')
        ) {
            sessionStorage.removeItem('token');
            window.dispatchEvent(new Event('session-expired'));
        }
        return Promise.reject(error);
    },
);
export const errorMessage = (error) =>
    error.response?.data?.msg ||
    (!error.response && error.isAxiosError
        ? 'The traffic service is unavailable. Check your connection and retry in a moment.'
        : error.message || 'Service unavailable. Check your connection and retry.');
export const localTime = (value) =>
    value
        ? new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
        : 'Source-relative time';
export async function download(path, filename) {
    const res = await http.get(path, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export default API_BASE;
