import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { api, auth } from './services/api';
import { User } from './types';

import Login from './pages/Login';
import Layout from './components/Layout';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!auth.token) {
      setLoading(false);
      return;
    }
    api
      .get<User>('/auth/me')
      .then((u) => {
        if (u.role !== 'admin') throw new Error('Không có quyền admin');
        setUser(u);
      })
      .catch(() => auth.set(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <main className="center">Đang khởi tạo ứng dụng Quản trị…</main>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <Login onSuccess={setUser} />} />
      <Route
        path="/*"
        element={
          user ? (
            <Layout
              user={user}
              onLogout={() => {
                auth.set(null);
                setUser(null);
              }}
            />
          ) : (
            <Navigate to="/login" />
          )
        }
      />
    </Routes>
  );
}
