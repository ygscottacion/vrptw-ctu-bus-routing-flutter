import { supabase } from './supabase';

export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const WS_URL = BASE_URL.replace(/^http/, 'ws').replace(/\/api\/v1$/, '/api/v1/ws/bus-locations');

// Cleanup legacy localStorage token once on module load
if (typeof localStorage !== 'undefined') {
  const legacyKey = ['ctu', 'admin', 'token'].join('_');
  localStorage.removeItem(legacyKey);
}

export type AuthFailureCallback = () => void;
let onAuthFailureHandler: AuthFailureCallback | null = null;

export function setAuthFailureHandler(handler: AuthFailureCallback | null) {
  onAuthFailureHandler = handler;
}

async function request<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const {
    data: { session }
  } = await supabase.auth.getSession();
  const token = session?.access_token;

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers
    }
  });

  if (response.status === 401) {
    if (!isRetry) {
      // Try refresh session exactly ONCE
      const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
      if (!refreshError && refreshData.session) {
        return request<T>(path, options, true);
      }
    }
    // Refresh failed or second 401 -> sign out and clear state
    await supabase.auth.signOut();
    if (onAuthFailureHandler) {
      onAuthFailureHandler();
    }
    throw new Error('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.');
  }

  if (response.status === 403) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Tài khoản thiếu quyền thực hiện thao tác này.');
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Lỗi ${response.status}`);
  }

  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T,>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T,>(path: string) => request<T>(path, { method: 'DELETE' })
};
