export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1';

export const WS_URL = BASE_URL.replace(/^http/, 'ws').replace(/\/api\/v1$/, '/api/v1/ws/bus-locations');

let token = localStorage.getItem('ctu_admin_token');

export const auth = {
  get token() {
    return token;
  },
  set(value: string | null) {
    token = value;
    if (value) {
      localStorage.setItem('ctu_admin_token', value);
    } else {
      localStorage.removeItem('ctu_admin_token');
    }
  }
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detailMsg = Array.isArray(data.detail) ? JSON.stringify(data.detail) : data.detail;
    throw new Error(detailMsg || `Lỗi ${response.status}`);
  }

  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

export const api = {
  login: async (username: string, password: string) => {
    const form = new URLSearchParams({ username, password });
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form
    });
    if (!response.ok) throw new Error('Sai tên đăng nhập hoặc mật khẩu');
    return response.json() as Promise<{ access_token: string }>;
  },
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T,>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T,>(path: string) => request<T>(path, { method: 'DELETE' })
};
