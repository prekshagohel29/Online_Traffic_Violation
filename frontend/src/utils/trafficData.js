// One authenticated API path. No direct browser access to the database.
import { http } from './api';
export async function fetchFines() {
    return (await http.get('/api/operator/memos')).data.items;
}
export async function fetchAnalytics() {
    return (await http.get('/api/gov/analytics')).data;
}
