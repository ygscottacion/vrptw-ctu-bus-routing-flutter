import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

function Vehicles() {
  const [items, setItems] = useState<Vehicle[]>([]);
  const [drivers, setDrivers] = useState<User[]>([]);
  const [error, setError] = useState('');

  const load = () => {
    api.get<Vehicle[]>('/vehicles/').then(setItems).catch((e) => setError(e.message));
    api.get<User[]>('/users/').then((users) => setDrivers(users.filter((u) => u.role === 'driver'))).catch(() => {});
  };

  useEffect(() => {
    void load();
  }, []);

  const add = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await api.post('/vehicles/', { license_plate: f.get('plate'), capacity: Number(f.get('capacity')) });
      e.currentTarget.reset();
      void load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const assignDriver = async (vehicleId: number, driverId: string) => {
    try {
      const dId = driverId ? Number(driverId) : null;
      await api.put(`/vehicles/${vehicleId}/driver?driver_id=${dId ?? ''}`);
      void load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Page title="Quản lý Xe buýt & Phân công Tài xế">
      <div className="two-col">
        <section className="panel">
          <h2>Thêm xe buýt mới</h2>
          <form className="inline-form" onSubmit={add}>
            <input name="plate" placeholder="Biển số xe (ví dụ: 65B-123.45)" required />
            <input name="capacity" type="number" min="1" defaultValue="30" placeholder="Sức chứa" required />
            <button>Thêm xe</button>
          </form>
        </section>
        <section className="panel muted">
          Mỗi xe buýt được gán cho một tài xế phụ trách chạy các tuyến trong ngày.
        </section>
      </div>

      {error && <div className="error">{error}</div>}

      <Table
        heads={['Biển số', 'Sức chứa', 'Tài xế phân công', 'Thao tác']}
        rows={items.map((v) => (
          <tr key={v.id}>
            <td>
              <b>{v.license_plate}</b>
            </td>
            <td>{v.capacity} chỗ</td>
            <td>
              <select
                value={v.driver?.id || v.driver_id || ''}
                onChange={(e) => assignDriver(v.id, e.target.value)}
                style={{ padding: '6px 10px', fontSize: 13 }}
              >
                <option value="">-- Chưa gán tài xế --</option>
                {drivers.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.full_name || d.username} (ID #{d.id})
                  </option>
                ))}
              </select>
            </td>
            <td>
              <button
                className="danger-button"
                onClick={async () => {
                  if (confirm(`Xóa xe ${v.license_plate}?`)) {
                    await api.delete(`/vehicles/${v.id}`);
                    void load();
                  }
                }}
              >
                Xóa
              </button>
            </td>
          </tr>
        ))}
      />
    </Page>
  );
}


export default Vehicles;
