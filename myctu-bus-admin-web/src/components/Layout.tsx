import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';

export const menu = [
  ['/dashboard', '▦', 'Tổng quan'],
  ['/map', '📍', 'Bản đồ Realtime'],
  ['/locations', '🚏', 'Trạm dừng'],
  ['/vehicles', '🚌', 'Xe buýt'],
  ['/routes', '⌁', 'Tuyến đường'],
  ['/users', '♙', 'Người dùng'],
  ['/incidents', '⚠', 'Sự cố'],
  ['/reports', '◔', 'Báo cáo'],
  ['/settings', '⚙', 'Cài đặt']
];

import Dashboard from '../pages/Dashboard';
import RealtimeMapPage from '../pages/RealtimeMapPage';
import Locations from '../pages/Locations';
import Vehicles from '../pages/Vehicles';
import RouteGenerator from '../pages/RouteGenerator';
import Users from '../pages/Users';
import Incidents from '../pages/Incidents';
import Reports from '../pages/Reports';
import Settings from '../pages/Settings';

function Layout({ user, onLogout }: { user: User; onLogout: () => void }) {
  const navigate = useNavigate();
  return (
    <div className="layout">
      <aside>
        <div className="logo">
          MYCTU <b>BUS</b>
          <small>ADMIN PORTAL</small>
        </div>
        <nav>
          {menu.map(([to, icon, text]) => (
            <NavLink key={to} to={to}>
              <span>{icon}</span>
              <span>{text}</span>
            </NavLink>
          ))}
        </nav>
        <button
          className="logout"
          onClick={() => {
            onLogout();
            navigate('/login');
          }}
        >
          ↪ Đăng xuất
        </button>
      </aside>
      <section className="content">
        <header>
          <div>
            <strong>Trung tâm Điều hành Xe buýt CTU</strong>
            <small>Hệ thống giám sát Realtime & Quản lý mạng lưới</small>
          </div>
          <div className="admin">
            {user.full_name || user.username}
            <span>Quản trị viên</span>
          </div>
        </header>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/map" element={<RealtimeMapPage />} />
          <Route path="/locations" element={<Locations />} />
          <Route path="/vehicles" element={<Vehicles />} />
          <Route path="/routes" element={<RouteGenerator />} />
          <Route path="/users" element={<Users />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Routes>
      </section>
    </div>
  );
}


export default Layout;
