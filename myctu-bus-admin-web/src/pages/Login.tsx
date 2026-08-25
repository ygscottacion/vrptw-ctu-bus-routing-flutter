import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

function Login({ onSuccess }: { onSuccess: (user: User) => void }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    const f = new FormData(e.currentTarget);
    try {
      const result = await api.login(String(f.get('username')), String(f.get('password')));
      auth.set(result.access_token);
      const user = await api.get<User>('/auth/me');
      if (user.role !== 'admin') throw new Error('Tài khoản này không có quyền quản trị.');
      onSuccess(user);
    } catch (e) {
      auth.set(null);
      setError(e instanceof Error ? e.message : 'Đăng nhập thất bại');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login">
      <form onSubmit={submit}>
        <span className="brand">
          MYCTU <b>BUS</b>
        </span>
        <h1>Quản trị hệ thống</h1>
        <p>Đăng nhập bằng tài khoản quản trị để theo dõi realtime & điều hành.</p>
        <label>
          Tên đăng nhập
          <input name="username" defaultValue="admin" required autoFocus />
        </label>
        <label>
          Mật khẩu
          <input name="password" type="password" defaultValue="admin123" required />
        </label>
        {error && <div className="error">{error}</div>}
        <button disabled={busy}>{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
      </form>
    </main>
  );
}


export default Login;
