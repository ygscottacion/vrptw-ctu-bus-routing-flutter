import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

function Incidents() {
  const [items, setItems] = useState<Incident[]>([]);
  const load = () => api.get<Incident[]>('/incidents/').then(setItems);

  useEffect(() => {
    void load();
  }, []);

  return (
    <Page title="Quản lý & Xử lý Sự cố">
      <Table
        heads={['ID', 'Tiêu đề sự cố', 'Mô tả chi tiết', 'Tài xế báo cáo', 'Thời gian', 'Trạng thái', 'Thao tác']}
        rows={items.map((i) => (
          <tr key={i.id}>
            <td>#{i.id}</td>
            <td>
              <b>{i.title}</b>
            </td>
            <td>{i.description || 'Không có chi tiết'}</td>
            <td>{i.driver?.full_name || i.driver?.username || `ID #${i.driver?.id || '—'}`}</td>
            <td>{new Date(i.reported_at).toLocaleString('vi-VN')}</td>
            <td>
              <span className={`badge ${i.status === 'resolved' ? '' : 'admin'}`}>{i.status === 'resolved' ? 'Đã giải quyết' : 'Chờ xử lý'}</span>
            </td>
            <td>
              {i.status !== 'resolved' && (
                <button
                  onClick={async () => {
                    await api.put(`/incidents/${i.id}/status`, { status: 'resolved' });
                    void load();
                  }}
                >
                  Đánh dấu Đã xử lý
                </button>
              )}
            </td>
          </tr>
        ))}
      />
    </Page>
  );
}


export default Incidents;
