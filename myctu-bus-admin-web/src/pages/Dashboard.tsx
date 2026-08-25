import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

function Dashboard() {
  const [data, setData] = useState<any>();
  useEffect(() => {
    api
      .get<any>('/reports/summary')
      .then(setData)
      .catch(() => setData({ error: true }));
  }, []);

  if (!data)
    return (
      <Page title="Tổng quan">
        <p>Đang tải dữ liệu tổng quan…</p>
      </Page>
    );

  if (data.error)
    return (
      <Page title="Tổng quan">
        <div className="error">Không kết nối được dịch vụ báo cáo tổng quan.</div>
      </Page>
    );

  const s = data.summary;
  return (
    <Page title="Tổng quan Trung tâm Điều hành">
      <div className="stats">
        <Stat label="Xe trong hệ thống" value={s.total_vehicles} icon="🚌" />
        <Stat label="Tuyến đã khởi tạo" value={s.total_routes} icon="⌁" />
        <Stat label="Sinh viên đã đăng ký" value={s.total_students} icon="♙" />
        <Stat label="Sự cố cần xử lý" value={s.pending_incidents} icon="⚠" danger={s.pending_incidents > 0} />
      </div>

      <div className="two-col">
        <section className="panel">
          <h2>
            Trạng thái vận hành chung <span className="ok">● {data.system_status}</span>
          </h2>
          <p>
            Đội xe buýt Đại học Cần Thơ đang hoạt động theo đúng lịch trình. Sử dụng mục <b>Bản đồ Realtime</b> để theo dõi chính xác vị trí GPS từng xe.
          </p>
          <div style={{ marginTop: 15 }}>
            <NavLink to="/map" className="badge" style={{ textDecoration: 'none', padding: '8px 14px', fontSize: 13 }}>
              📍 Mở bản đồ giám sát Realtime →
            </NavLink>
          </div>
        </section>

        <section className="panel">
          <h2>Tác vụ quản trị nhanh</h2>
          <ul style={{ paddingLeft: 18, margin: 0, color: '#486069', fontSize: 14, lineHeight: 1.8 }}>
            <li>Thêm/Phân công tài xế cho xe</li>
            <li>Tạo tuyến chạy tự động cho ngày mới</li>
            <li>Duyệt sự cố do tài xế gửi lên</li>
            <li>Quản lý phân quyền tài khoản</li>
          </ul>
        </section>
      </div>
    </Page>
  );
}


export default Dashboard;
