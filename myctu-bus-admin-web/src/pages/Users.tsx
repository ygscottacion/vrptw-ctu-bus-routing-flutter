import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

function Users() {
  const [items, setItems] = useState<User[]>([]);
  const [roleFilter, setRoleFilter] = useState('all');

  const load = () => api.get<User[]>('/users/').then(setItems);

  useEffect(() => {
    void load();
  }, []);

  const changeRole = async (userId: number, newRole: string) => {
    try {
      await api.put(`/users/${userId}/role`, { role: newRole });
      void load();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const filtered = roleFilter === 'all' ? items : items.filter((u) => u.role === roleFilter);

  return (
    <Page title="Quản lý Tài khoản Người dùng">
      <div className="panel" style={{ display: 'flex', gap: 15, alignItems: 'center' }}>
        <span>Lọc theo vai trò:</span>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
          <option value="all">Tất cả người dùng ({items.length})</option>
          <option value="student">Sinh viên ({items.filter((u) => u.role === 'student').length})</option>
          <option value="driver">Tài xế ({items.filter((u) => u.role === 'driver').length})</option>
          <option value="admin">Quản trị viên ({items.filter((u) => u.role === 'admin').length})</option>
        </select>
      </div>

      <Table
        heads={['ID', 'Tài khoản', 'Họ tên', 'Điện thoại', 'Vai trò hiện tại', 'Thay đổi vai trò']}
        rows={filtered.map((u) => (
          <tr key={u.id}>
            <td>#{u.id}</td>
            <td>
              <b>{u.username}</b>
            </td>
            <td>{u.full_name || '—'}</td>
            <td>{u.phone || '—'}</td>
            <td>
              <span className={`badge ${u.role}`}>{u.role === 'student' ? 'Sinh viên' : u.role === 'driver' ? 'Tài xế' : 'Quản trị viên'}</span>
            </td>
            <td>
              <select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)} style={{ padding: '4px 8px', fontSize: 13 }}>
                <option value="student">Sinh viên</option>
                <option value="driver">Tài xế</option>
                <option value="admin">Admin</option>
              </select>
            </td>
          </tr>
        ))}
      />
    </Page>
  );
}


export default Users;
