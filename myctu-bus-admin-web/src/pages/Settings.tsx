import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

function Settings() {
  return (
    <Page title="Cài đặt Hệ thống">
      <section className="panel">
        <h2>Cấu hình Kết nối Backend & Realtime Service</h2>
        <p>
          Địa chỉ REST API: <code>{import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'}</code>
        </p>
        <p>
          Kênh Realtime WebSocket: <code>{WS_URL}</code>
        </p>
      </section>
    </Page>
  );
}


export default Settings;
