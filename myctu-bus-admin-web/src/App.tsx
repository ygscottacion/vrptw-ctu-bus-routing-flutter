import { FormEvent, ReactNode, useEffect, useRef, useState } from 'react';
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import { api, auth, WS_URL } from './services/api';

type User = { id: string; username: string; full_name?: string; phone?: string; role: string };
type Vehicle = { id: string; license_plate: string; capacity: number; driver?: User; driver_id?: string };
type Incident = { id: string; title: string; description?: string; status: string; reported_at: string; driver?: User };
type BusLocation = { vehicle_id: string; license_plate?: string; latitude: number; longitude: number; speed?: number; status?: string };
type LocationItem = { id: string; code?: string; name: string; latitude: number; longitude: number };
type RouteStop = { id: string; route_id: string; location_id: string; stop_order: number; arrival_time?: string; location?: LocationItem };
type RouteItem = {
  id: string;
  route_job_id?: string;
  service_date: string;
  session_id: string;
  trip_type: string;
  vehicle_id?: string;
  status: 'pending' | 'approved' | 'rejected' | 'in_progress' | 'completed';
  total_distance: number;
  stops: RouteStop[];
  passenger_count?: number;
  vehicle?: Vehicle;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
};

declare global {
  interface Window {
    L: any;
  }
}

const menu = [
  ['/dashboard', '▦', 'Tổng quan'],
  ['/map', '📍', 'Bản đồ Realtime'],
  ['/vehicles', '🚌', 'Xe buýt'],
  ['/routes', '⌁', 'Tuyến đường & Duyệt'],
  ['/users', '♙', 'Người dùng'],
  ['/incidents', '⚠', 'Sự cố'],
  ['/reports', '◔', 'Báo cáo'],
  ['/settings', '⚙', 'Cài đặt']
];

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

function Page({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="page">
      <h1>{title}</h1>
      {children}
    </main>
  );
}

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

  const s = data.summary || {};
  return (
    <Page title="Tổng quan Trung tâm Điều hành">
      <div className="stats">
        <Stat label="Xe trong hệ thống" value={s.total_vehicles ?? 0} icon="🚌" />
        <Stat label="Tuyến đã khởi tạo" value={s.total_routes ?? 0} icon="⌁" />
        <Stat label="Sinh viên đã đăng ký" value={s.total_students ?? 0} icon="♙" />
        <Stat label="Sự cố cần xử lý" value={s.pending_incidents ?? 0} icon="⚠" danger={(s.pending_incidents ?? 0) > 0} />
      </div>

      <div className="two-col">
        <section className="panel">
          <h2>
            Trạng thái vận hành chung <span className="ok">● {data.system_status || 'ONLINE'}</span>
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
            <li>Tạo tuyến chạy tự động & Duyệt lộ trình</li>
            <li>Duyệt sự cố do tài xế gửi lên</li>
            <li>Quản lý phân quyền tài khoản (Sinh viên, Tài xế, Admin)</li>
          </ul>
        </section>
      </div>
    </Page>
  );
}

function Stat({ label, value, icon, danger }: any) {
  return (
    <article className={'stat ' + (danger ? 'danger' : '')}>
      <span>{icon}</span>
      <strong>{value}</strong>
      <small>{label}</small>
    </article>
  );
}

function RealtimeMapPage() {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<any>(null);
  const markersRef = useRef<Record<string, any>>({});
  const [buses, setBuses] = useState<BusLocation[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [vehiclesList, setVehiclesList] = useState<Vehicle[]>([]);

  useEffect(() => {
    api.get<Vehicle[]>('/vehicles/').then(setVehiclesList).catch(() => {});
  }, []);

  const updateMarkers = (locations: BusLocation[]) => {
    if (!leafletMap.current || !window.L) return;

    locations.forEach((bus) => {
      const { vehicle_id, license_plate, latitude, longitude, speed = 0, status = 'in_progress' } = bus;

      const popupContent = `
        <div class="bus-popup">
          <h4>🚌 Xe ${license_plate || `#${vehicle_id.slice(0, 8)}`}</h4>
          <p>Tốc độ: <b>${speed} km/h</b></p>
          <p>Tọa độ: <code>${latitude.toFixed(4)}, ${longitude.toFixed(4)}</code></p>
          <p>Trạng thái: <span class="bus-status-tag ${status}">${status === 'in_progress' ? 'Đang chạy' : 'Đang chờ'}</span></p>
        </div>
      `;

      if (markersRef.current[vehicle_id]) {
        markersRef.current[vehicle_id].setLatLng([latitude, longitude]);
        markersRef.current[vehicle_id].setPopupContent(popupContent);
      } else {
        const marker = window.L.marker([latitude, longitude]).addTo(leafletMap.current);
        marker.bindPopup(popupContent);
        markersRef.current[vehicle_id] = marker;
      }
    });
  };

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return;

    if (window.L) {
      const map = window.L.map(mapRef.current).setView([10.0305, 105.7684], 15);
      const goongTileKey = (import.meta as any).env?.VITE_GOONG_MAPTILES_KEY || 'rwZKp27qLAlPcckb3HOe3E4JwiOaR54wPiW9hwJx';
      window.L.tileLayer(`https://tiles.goong.io/assets/tiles/{z}/{x}/{y}.png?api_key=${goongTileKey}`, {
        attribution: '&copy; Goong Maps'
      }).addTo(map);
      leafletMap.current = map;
    }
  }, []);

  useEffect(() => {
    let socket: WebSocket | null = null;
    try {
      socket = new WebSocket(WS_URL);
      socket.onopen = () => setWsConnected(true);
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload && payload.vehicle_id) {
            setBuses((prev) => {
              const idx = prev.findIndex((b) => b.vehicle_id === payload.vehicle_id);
              let updated: BusLocation[];
              if (idx >= 0) {
                updated = [...prev];
                updated[idx] = { ...updated[idx], ...payload };
              } else {
                updated = [...prev, payload];
              }
              updateMarkers(updated);
              return updated;
            });
          }
        } catch (e) {}
      };
      socket.onerror = () => setWsConnected(false);
      socket.onclose = () => setWsConnected(false);
    } catch (e) {
      setWsConnected(false);
    }

    return () => {
      if (socket) socket.close();
    };
  }, []);

  const centerBus = (bus: BusLocation) => {
    if (leafletMap.current) {
      leafletMap.current.setView([bus.latitude, bus.longitude], 17);
      if (markersRef.current[bus.vehicle_id]) {
        markersRef.current[bus.vehicle_id].openPopup();
      }
    }
  };

  return (
    <Page title="Bản đồ Giám sát Xe buýt Realtime">
      <div className="live-feed-bar">
        <div>
          <span className="pulse-dot" />
          Kênh giám sát vị trí GPS trực tiếp {wsConnected ? '(Đã kết nối WebSocket)' : '(Chờ kết nối Realtime GPS từ tài xế)'}
        </div>
        <small style={{ opacity: 0.9 }}>Cập nhật 15s/lần</small>
      </div>

      <div className="two-col">
        <div ref={mapRef} className="map-container" />

        <section className="panel" style={{ height: 520, overflowY: 'auto' }}>
          <h2>Danh sách xe buýt đang phát GPS ({buses.length})</h2>
          {buses.length === 0 ? (
            <p style={{ color: '#708187', fontSize: 14 }}>Hiện chưa có xe buýt nào phát GPS trong ca làm việc.</p>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {buses.map((bus) => {
                const matchedVeh = vehiclesList.find((v) => v.id === bus.vehicle_id);
                return (
                  <article
                    key={bus.vehicle_id}
                    onClick={() => centerBus(bus)}
                    style={{
                      padding: 12,
                      borderRadius: 8,
                      border: '1px solid #e2eaec',
                      cursor: 'pointer',
                      background: '#fcfdfe'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong style={{ color: '#087b7c' }}>
                        🚌 {bus.license_plate || matchedVeh?.license_plate || `Xe #${bus.vehicle_id.slice(0, 8)}`}
                      </strong>
                      <span className={`bus-status-tag ${bus.status || 'in_progress'}`}>
                        {bus.status === 'in_progress' ? 'Đang chạy' : 'Đang dừng'}
                      </span>
                    </div>
                    <small style={{ color: '#65777d', display: 'block', marginTop: 4 }}>
                      Tài xế: {matchedVeh?.driver?.full_name || matchedVeh?.driver?.username || 'Đang phân công'}
                    </small>
                    <small style={{ color: '#087b7c', display: 'block', marginTop: 2 }}>
                      Tốc độ: {bus.speed ?? 0} km/h • Click để xem vị trí trên bản đồ
                    </small>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </Page>
  );
}

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

  const assignDriver = async (vehicleId: string, driverId: string) => {
    try {
      await api.put(`/vehicles/${vehicleId}/driver?driver_id=${driverId || ''}`);
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
                    {d.full_name || d.username}
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

function Users() {
  const [items, setItems] = useState<User[]>([]);
  const [roleFilter, setRoleFilter] = useState('all');

  const load = () => api.get<User[]>('/users/').then(setItems);

  useEffect(() => {
    void load();
  }, []);

  const changeRole = async (userId: string, newRole: string) => {
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
          <option value="student">Sinh viên ({items.filter((u) => u.role === 'student' || u.role === 'passenger').length})</option>
          <option value="driver">Tài xế ({items.filter((u) => u.role === 'driver').length})</option>
          <option value="admin">Quản trị viên ({items.filter((u) => u.role === 'admin').length})</option>
        </select>
      </div>

      <Table
        heads={['Tài khoản', 'Họ tên', 'Điện thoại', 'Vai trò hiện tại', 'Thay đổi vai trò']}
        rows={filtered.map((u) => (
          <tr key={u.id}>
            <td>
              <b>{u.username}</b>
            </td>
            <td>{u.full_name || '—'}</td>
            <td>{u.phone || '—'}</td>
            <td>
              <span className={`badge ${u.role}`}>
                {u.role === 'student' || u.role === 'passenger' ? 'Sinh viên' : u.role === 'driver' ? 'Tài xế' : 'Quản trị viên'}
              </span>
            </td>
            <td>
              <select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)} style={{ padding: '4px 8px', fontSize: 13 }}>
                <option value="passenger">Sinh viên</option>
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

function Incidents() {
  const [items, setItems] = useState<Incident[]>([]);
  const load = () => api.get<Incident[]>('/incidents/').then(setItems);

  useEffect(() => {
    void load();
  }, []);

  return (
    <Page title="Quản lý & Xử lý Sự cố">
      <Table
        heads={['Tiêu đề sự cố', 'Mô tả chi tiết', 'Tài xế báo cáo', 'Thời gian', 'Trạng thái', 'Thao tác']}
        rows={items.map((i) => (
          <tr key={i.id}>
            <td>
              <b>{i.title}</b>
            </td>
            <td>{i.description || 'Không có chi tiết'}</td>
            <td>{i.driver?.full_name || i.driver?.username || '—'}</td>
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

function RouteGenerator() {
  const [locations, setLocations] = useState<LocationItem[]>([]);
  const [routes, setRoutes] = useState<RouteItem[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(true);
  const [jobStatus, setJobStatus] = useState<{ id: string; status: string; message?: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [selectedRouteForStops, setSelectedRouteForStops] = useState<RouteItem | null>(null);

  const loadLocations = async () => {
    try {
      const locs = await api.get<LocationItem[]>('/locations/');
      setLocations(locs);
    } catch (_) {
    } finally {
      setLoadingLocations(false);
    }
  };

  const loadRoutes = async () => {
    try {
      const r = await api.get<RouteItem[]>('/routes/');
      setRoutes(r);
    } catch (_) {}
  };

  useEffect(() => {
    void loadLocations();
    void loadRoutes();
  }, []);

  const pollJobStatus = async (jobId: string) => {
    try {
      const job = await api.get<{ job_id: string; status: string; error_message?: string }>(`/routes/jobs/${jobId}`);
      setJobStatus({ id: jobId, status: job.status, message: job.error_message });
      if (job.status === 'QUEUED' || job.status === 'RUNNING') {
        setTimeout(() => pollJobStatus(jobId), 2000);
      } else {
        setSubmitting(false);
        if (job.status === 'SUCCEEDED') {
          void loadRoutes();
        }
      }
    } catch (e) {
      setJobStatus({ id: jobId, status: 'FAILED', message: (e as Error).message });
      setSubmitting(false);
    }
  };

  const submitGenerate = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitting(true);
    setJobStatus(null);
    const f = new FormData(e.currentTarget);
    const payload = {
      service_date: String(f.get('service_date')),
      session_id: String(f.get('session_id')),
      trip_type: String(f.get('trip_type')),
      depot_location_id: String(f.get('depot_location_id'))
    };

    try {
      const res = await api.post<{ job_id: string; status: string }>('/routes/admin/generate', payload);
      setJobStatus({ id: res.job_id, status: res.status });
      pollJobStatus(res.job_id);
    } catch (e) {
      setJobStatus({ id: '', status: 'FAILED', message: (e as Error).message });
      setSubmitting(false);
    }
  };

  const approveRoute = async (routeId: string) => {
    try {
      await api.post(`/routes/${routeId}/approve`);
      void loadRoutes();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const rejectRoute = async (routeId: string) => {
    const reason = prompt('Nhập lý do từ chối tuyến buýt này:');
    if (!reason || !reason.trim()) return;
    try {
      await api.post(`/routes/${routeId}/reject`, { reason: reason.trim() });
      void loadRoutes();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const defaultDate = new Date(Date.now() + 86400000).toISOString().split('T')[0];

  return (
    <Page title="Tạo Tuyến & Duyệt Lộ trình Xe buýt (Admin)">
      <section className="panel">
        <h2>Khởi tạo Tác vụ Sinh tuyến Tự động (Sweep + Tabu Search)</h2>
        <p>Chọn trạm depot xuất phát, ngày chạy, ca làm việc và chiều đi/về để chạy solver phân bổ tuyến buýt.</p>

        <form className="inline-form" onSubmit={submitGenerate} style={{ flexWrap: 'wrap', gap: 12 }}>
          <label style={{ display: 'flex', flexDirection: 'column', fontSize: 13, gap: 4 }}>
            Ngày chạy (service_date):
            <input name="service_date" type="date" defaultValue={defaultDate} required style={{ padding: '6px 10px' }} />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', fontSize: 13, gap: 4 }}>
            Ca làm việc:
            <select name="session_id" required style={{ padding: '6px 10px' }}>
              <option value="MORNING_1">Ca sáng 1 (MORNING_1)</option>
              <option value="MORNING_2">Ca sáng 2 (MORNING_2)</option>
              <option value="NOON_1">Ca trưa 1 (NOON_1)</option>
              <option value="NOON_2">Ca trưa 2 (NOON_2)</option>
            </select>
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', fontSize: 13, gap: 4 }}>
            Chiều di chuyển:
            <select name="trip_type" required style={{ padding: '6px 10px' }}>
              <option value="pickup">Đưa đón (pickup)</option>
              <option value="dropoff">Trả khách (dropoff)</option>
            </select>
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', fontSize: 13, gap: 4 }}>
            Trạm depot xuất phát:
            <select name="depot_location_id" required disabled={loadingLocations} style={{ padding: '6px 10px', minWidth: 200 }}>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name} {loc.code ? `(${loc.code})` : ''}
                </option>
              ))}
            </select>
          </label>

          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button disabled={submitting}>{submitting ? 'Đang tạo & chạy solver…' : 'Khởi tạo Tuyến'}</button>
          </div>
        </form>

        {jobStatus && (
          <div
            className={`notice ${jobStatus.status === 'FAILED' ? 'error' : ''}`}
            style={{
              marginTop: 16,
              padding: 12,
              borderRadius: 6,
              background: jobStatus.status === 'SUCCEEDED' ? '#e6f7ed' : jobStatus.status === 'FAILED' ? '#fde8e8' : '#e6f0fa',
              border: `1px solid ${jobStatus.status === 'SUCCEEDED' ? '#a3e0b8' : jobStatus.status === 'FAILED' ? '#f8b4b4' : '#b3d4fc'}`
            }}
          >
            <strong>Trạng thái tác vụ: {jobStatus.status}</strong>
            {jobStatus.id && <span style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>(Job ID: {jobStatus.id})</span>}
            {jobStatus.status === 'RUNNING' && <p style={{ margin: '4px 0 0' }}>Solver đang chạy phân bổ trạm đón và xe buýt...</p>}
            {jobStatus.status === 'SUCCEEDED' && <p style={{ margin: '4px 0 0', color: '#155724' }}>✓ Sinh tuyến thành công! Danh sách các tuyến xe bên dưới đã được cập nhật.</p>}
            {jobStatus.status === 'FAILED' && <p style={{ margin: '4px 0 0', color: '#721c24' }}>Lỗi: {jobStatus.message || 'Chạy job thất bại.'}</p>}
          </div>
        )}
      </section>

      <section className="panel" style={{ marginTop: 20 }}>
        <h2>Danh sách Tuyến buýt & Luồng Duyệt lộ trình ({routes.length})</h2>
        <Table
          heads={['Mã / ID Tuyến', 'Ngày chạy', 'Ca / Chiều', 'Xe gán', 'Số SV đón', 'Quãng đường', 'Trạng thái', 'Thao tác duyệt / Manifest']}
          rows={routes.map((r) => (
            <tr key={r.id}>
              <td>
                <b style={{ color: '#087b7c' }}>CT-{r.id.slice(0, 8).toUpperCase()}</b>
              </td>
              <td>{r.service_date}</td>
              <td>
                {r.session_id} • {r.trip_type === 'pickup' ? 'Đón' : 'Trả'}
              </td>
              <td>{r.vehicle?.license_plate || (r.vehicle_id ? `Xe #${r.vehicle_id.slice(0, 8)}` : 'Chưa gán xe')}</td>
              <td>{r.passenger_count ?? 0} sinh viên</td>
              <td>{r.total_distance?.toFixed(1) ?? '0.0'} km</td>
              <td>
                <span className={`badge ${r.status}`}>
                  {r.status === 'pending'
                    ? 'Chờ duyệt'
                    : r.status === 'approved'
                    ? 'Đã duyệt'
                    : r.status === 'rejected'
                    ? 'Từ chối'
                    : r.status === 'in_progress'
                    ? 'Đang chạy'
                    : 'Hoàn tất'}
                </span>
              </td>
              <td style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <button style={{ fontSize: 12, padding: '4px 8px' }} onClick={() => setSelectedRouteForStops(r)}>
                  👁 Xem trạm dừng ({r.stops?.length ?? 0})
                </button>
                {r.status === 'pending' && (
                  <>
                    <button style={{ fontSize: 12, padding: '4px 8px', background: '#087b7c' }} onClick={() => approveRoute(r.id)}>
                      ✓ Duyệt
                    </button>
                    <button className="danger-button" style={{ fontSize: 12, padding: '4px 8px' }} onClick={() => rejectRoute(r.id)}>
                      ✕ Từ chối
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        />
      </section>

      {/* Modal / Drawer hiển thị Manifest danh sách trạm dừng */}
      {selectedRouteForStops && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
          onClick={() => setSelectedRouteForStops(null)}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: 8,
              padding: 24,
              maxWidth: 600,
              width: '90%',
              maxHeight: '80vh',
              overflowY: 'auto'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3>
              Lộ trình Chi tiết: Tuyến CT-{selectedRouteForStops.id.slice(0, 8).toUpperCase()} ({selectedRouteForStops.service_date})
            </h3>
            <p style={{ color: '#666', fontSize: 13 }}>
              Xe phụ trách: <b>{selectedRouteForStops.vehicle?.license_plate || 'Chưa phân công'}</b> • Sức chứa:{' '}
              {selectedRouteForStops.vehicle?.capacity ?? '—'} chỗ • Số sinh viên gán: <b>{selectedRouteForStops.passenger_count ?? 0}</b>
            </p>

            <table style={{ width: '100%', marginTop: 15, borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f5f5f5', textAlign: 'left' }}>
                  <th style={{ padding: 8 }}>STT</th>
                  <th style={{ padding: 8 }}>Mã trạm</th>
                  <th style={{ padding: 8 }}>Tên trạm dừng</th>
                  <th style={{ padding: 8 }}>Dự kiến đến</th>
                </tr>
              </thead>
              <tbody>
                {(selectedRouteForStops.stops || [])
                  .sort((a, b) => a.stop_order - b.stop_order)
                  .map((stop) => (
                    <tr key={stop.id} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: 8 }}>#{stop.stop_order}</td>
                      <td style={{ padding: 8 }}>
                        <code>{stop.location?.code || stop.location_id.slice(0, 8)}</code>
                      </td>
                      <td style={{ padding: 8 }}>
                        <b>{stop.location?.name || 'Trạm đón'}</b>
                      </td>
                      <td style={{ padding: 8 }}>
                        {stop.arrival_time ? new Date(stop.arrival_time).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>

            <div style={{ marginTop: 20, textAlign: 'right' }}>
              <button onClick={() => setSelectedRouteForStops(null)}>Đóng</button>
            </div>
          </div>
        </div>
      )}
    </Page>
  );
}

function Reports() {
  return (
    <Page title="Báo cáo & Thống kê Vận hành">
      <div className="stats">
        <Stat label="Tổng lượt sinh viên đã đón" value="1,240" icon="🚌" />
        <Stat label="Tỷ lệ đúng giờ" value="98.5%" icon="⏱" />
        <Stat label="Doanh thu bán vé tháng" value="18.5M" icon="💳" />
        <Stat label="Đánh giá trung bình" value="4.9/5" icon="⭐" />
      </div>

      <section className="panel">
        <h2>Doanh thu & Lưu lượng sử dụng xe buýt</h2>
        <p>Báo cáo tổng hợp số lượt di chuyển của sinh viên Đại học Cần Thơ trên tất cả các tuyến cố định và tuyến đưa đón campus.</p>
      </section>
    </Page>
  );
}

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

function Table({ heads, rows }: { heads: string[]; rows: ReactNode[] }) {
  return (
    <section className="panel table-wrap">
      <table>
        <thead>
          <tr>
            {heads.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      {!rows.length && <p style={{ padding: 20, textAlign: 'center', color: '#708187' }}>Chưa có dữ liệu trong hệ thống.</p>}
    </section>
  );
}
