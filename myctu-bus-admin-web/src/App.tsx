import { FormEvent, ReactNode, useEffect, useRef, useState } from 'react';
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import { api, auth, WS_URL } from './services/api';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

type User = { id: number; username: string; full_name?: string; phone?: string; role: string };
type Vehicle = { id: number; license_plate: string; capacity: number; driver?: User; driver_id?: number; status?: 'idle' | 'running' | 'broken' };

const VEHICLE_STATUS_META: Record<string, { label: string; bg: string; color: string }> = {
  running: { label: 'Đang chạy', bg: 'var(--success-bg)', color: 'var(--success-text)' },
  idle: { label: 'Rảnh', bg: 'var(--info-bg)', color: 'var(--info-text)' },
  broken: { label: 'Gặp sự cố', bg: 'var(--danger-bg)', color: 'var(--danger-text)' },
};
type Incident = { id: number; title: string; description?: string; status: string; reported_at: string; driver?: User };
type BusLocation = { vehicle_id: number; license_plate?: string; latitude: number; longitude: number; speed?: number; status?: string };
type Ticket = { id: number; qr_code: string; route_id?: number; status: 'active' | 'used' | 'expired'; price: number; created_at: string };

type FleetStatus = {
  total_vehicles: number;
  running_count: number;
  broken_count: number;
  idle_count: number;
  running: { vehicle_id: number; license_plate: string; route_id: number | null }[];
  broken: { vehicle_id: number; license_plate: string; incident_id: number | null; incident_title: string | null }[];
  idle: { vehicle_id: number; license_plate: string }[];
};

type RoutesToday = {
  date: string;
  total: number;
  by_status: Record<string, number>;
  routes: { id: number; vehicle_id: number; license_plate: string | null; status: string; total_distance: number }[];
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
  ['/routes', '⌁', 'Tuyến đường'],
  ['/users', '♙', 'Người dùng'],
  ['/incidents', '⚠', 'Sự cố'],
  ['/tickets', '🎫', 'Vé'],
  ['/reports', '◔', 'Báo cáo'],
  ['/settings', '⚙', 'Cài đặt']
];

const STATUS_COLORS: Record<string, string> = {
  running: '#1b9e6b',
  broken: '#d64545',
  idle: '#9aa6a4',
  pending: '#e0a418',
  in_progress: '#087b7c',
  completed: '#1b9e6b',
};

const ROUTE_STATUS_LABEL: Record<string, string> = {
  pending: 'Chưa bắt đầu',
  in_progress: 'Đang chạy',
  completed: 'Hoàn thành',
};

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'object' && err !== null) {
    const anyErr = err as any;
    if (typeof anyErr.detail === 'string') return anyErr.detail;
    if (Array.isArray(anyErr.detail)) {
      return anyErr.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
    }
    if (typeof anyErr.message === 'string') return anyErr.message;
    try {
      return JSON.stringify(anyErr);
    } catch {
      return 'Đã có lỗi xảy ra';
    }
  }
  return String(err);
}

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

function getInitialTheme(): 'light' | 'dark' {
  const saved = localStorage.getItem('ctu-theme');
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function Layout({ user, onLogout }: { user: User; onLogout: () => void }) {
  const navigate = useNavigate();

  const [theme, setTheme] = useState<'light' | 'dark'>(getInitialTheme);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('ctu-sidebar-collapsed') === '1');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ctu-theme', theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem('ctu-sidebar-collapsed', collapsed ? '1' : '0');
  }, [collapsed]);

  return (
    <div className={'layout' + (collapsed ? ' collapsed' : '')}>
      <aside>
        <div className="sidebar-top">
          <div className="logo">
            {collapsed ? (
              <span>CTU</span>
            ) : (
              <>
                MYCTU <b>BUS</b>
                <small>ADMIN PORTAL</small>
              </>
            )}
          </div>
          <button
            className="sidebar-toggle"
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? 'Mở rộng sidebar' : 'Thu gọn sidebar'}
          >
            {collapsed ? '»' : '«'}
          </button>
        </div>
        <nav>
          {menu.map(([to, icon, text]) => (
            <NavLink key={to} to={to} title={collapsed ? text : undefined}>
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
          title={collapsed ? 'Đăng xuất' : undefined}
        >
          <span>↪</span> <span>Đăng xuất</span>
        </button>
      </aside>
      <section className="content">
        <header>
          <div>
            <strong>Trung tâm Điều hành Xe buýt CTU</strong>
            <small>Hệ thống giám sát Realtime & Quản lý mạng lưới</small>
          </div>
          <div className="header-actions">
            <button
              className="theme-toggle"
              onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
              title={theme === 'light' ? 'Chuyển sang dark mode' : 'Chuyển sang light mode'}
            >
              {theme === 'light' ? '🌙' : '☀️'}
            </button>
            <div className="admin">
              {user.full_name || user.username}
              <span>Quản trị viên</span>
            </div>
          </div>
        </header>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/map" element={<RealtimeMapPage />} />
          <Route path="/vehicles" element={<Vehicles />} />
          <Route path="/routes" element={<RouteGenerator />} />
          <Route path="/users" element={<Users currentUserId={user.id} />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/tickets" element={<Tickets />} />
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

  const [fleet, setFleet] = useState<FleetStatus | null>(null);
  const [fleetLoading, setFleetLoading] = useState(true);

  const [routesToday, setRoutesToday] = useState<RoutesToday | null>(null);
  const [routesLoading, setRoutesLoading] = useState(true);

  useEffect(() => {
    api
      .get<any>('/reports/summary')
      .then(setData)
      .catch(() => setData({ error: true }));
  }, []);

  useEffect(() => {
    setFleetLoading(true);
    api
      .get<FleetStatus>('/reports/fleet-status')
      .then(setFleet)
      .catch(() => setFleet(null))
      .finally(() => setFleetLoading(false));
  }, []);

  useEffect(() => {
    setRoutesLoading(true);
    api
      .get<RoutesToday>('/reports/routes-today')
      .then(setRoutesToday)
      .catch(() => setRoutesToday(null))
      .finally(() => setRoutesLoading(false));
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

  const fleetPieData = fleet
    ? [
      { name: 'Đang chạy', value: fleet.running_count, key: 'running' },
      { name: 'Gặp sự cố', value: fleet.broken_count, key: 'broken' },
      { name: 'Rảnh', value: fleet.idle_count, key: 'idle' },
    ].filter((d) => d.value > 0)
    : [];

  const routeStatusData = routesToday
    ? Object.entries(routesToday.by_status).map(([status, count]) => ({
      status: ROUTE_STATUS_LABEL[status] || status,
      statusKey: status,
      count,
    }))
    : [];

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

      {/* ============ Xe buýt hôm nay ============ */}
      <section className="panel" style={{ marginTop: 20 }}>
        <h2 style={{ marginBottom: 12 }}>Xe buýt hôm nay</h2>

        {fleetLoading ? (
          <p>Đang tải trạng thái đội xe…</p>
        ) : !fleet ? (
          <p style={{ color: '#708187' }}>Không tải được dữ liệu đội xe.</p>
        ) : (
          <>
            <div className="stats" style={{ marginBottom: 16 }}>
              <Stat label="Tổng số xe" value={fleet.total_vehicles} icon="🚌" />
              <Stat label="Đang chạy" value={fleet.running_count} icon="🟢" />
              <Stat label="Gặp sự cố" value={fleet.broken_count} icon="⚠" danger={fleet.broken_count > 0} />
            </div>

            <div className="two-col">
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={fleetPieData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={2}>
                      {fleetPieData.map((d) => (
                        <Cell key={d.key} fill={STATUS_COLORS[d.key]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div>
                  <p style={{ fontSize: 12, color: '#708187', margin: '0 0 6px', fontWeight: 600 }}>ĐANG CHẠY</p>
                  {fleet.running.length === 0 ? (
                    <p style={{ fontSize: 13, color: '#9aa6a4' }}>Không có xe nào đang chạy.</p>
                  ) : (
                    fleet.running.map((r) => (
                      <div key={r.vehicle_id} style={{ fontSize: 13, padding: '4px 0', display: 'flex', justifyContent: 'space-between' }}>
                        <span>
                          <b>{r.license_plate}</b>
                        </span>
                        <span style={{ color: '#708187' }}>{r.route_id ? `Tuyến #${r.route_id}` : '—'}</span>
                      </div>
                    ))
                  )}
                </div>
                <div>
                  <p style={{ fontSize: 12, color: '#708187', margin: '0 0 6px', fontWeight: 600 }}>GẶP SỰ CỐ</p>
                  {fleet.broken.length === 0 ? (
                    <p style={{ fontSize: 13, color: '#9aa6a4' }}>Không có xe nào gặp sự cố.</p>
                  ) : (
                    fleet.broken.map((b) => (
                      <div key={b.vehicle_id} style={{ fontSize: 13, padding: '4px 0', display: 'flex', justifyContent: 'space-between' }}>
                        <span>
                          <b>{b.license_plate}</b>
                        </span>
                        <span style={{ color: '#d64545' }}>{b.incident_title || '—'}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      {/* ============ Tuyến hôm nay ============ */}
      <section className="panel" style={{ marginTop: 20 }}>
        <h2 style={{ marginBottom: 12 }}>Tuyến hôm nay {routesToday ? `(${routesToday.date})` : ''}</h2>

        {routesLoading ? (
          <p>Đang tải dữ liệu tuyến…</p>
        ) : !routesToday || routesToday.total === 0 ? (
          <p style={{ color: '#708187' }}>Chưa có tuyến nào được khởi tạo hôm nay.</p>
        ) : (
          <div className="two-col">
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={routeStatusData} margin={{ left: -20, right: 8 }}>
                  <CartesianGrid stroke="#e2eaec" vertical={false} />
                  <XAxis dataKey="status" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={30} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {routeStatusData.map((d) => (
                      <Cell key={d.statusKey} fill={STATUS_COLORS[d.statusKey] || '#087b7c'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={{ maxHeight: 200, overflowY: 'auto' }}>
              {routesToday.routes.map((r) => (
                <div
                  key={r.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 13,
                    padding: '6px 0',
                    borderBottom: '1px solid #eef2f2',
                  }}
                >
                  <span>
                    Tuyến #{r.id} · {r.license_plate || `Xe #${r.vehicle_id}`}
                  </span>
                  <span style={{ color: '#708187' }}>{r.total_distance} km</span>
                  <span className="badge">{ROUTE_STATUS_LABEL[r.status] || r.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
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
  const markersRef = useRef<Record<number, any>>({});
  const [buses, setBuses] = useState<BusLocation[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [vehiclesList, setVehiclesList] = useState<Vehicle[]>([]);

  // Default CTU Can Tho locations for mock/live buses
  const defaultBuses: BusLocation[] = [
    { vehicle_id: 1, license_plate: '65B-123.45', latitude: 10.0305, longitude: 105.7684, speed: 28, status: 'in_progress' },
    { vehicle_id: 2, license_plate: '65B-678.90', latitude: 10.0271, longitude: 105.772, speed: 32, status: 'in_progress' },
    { vehicle_id: 3, license_plate: '65B-999.88', latitude: 10.034, longitude: 105.7645, speed: 0, status: 'idle' }
  ];

  useEffect(() => {
    api.get<Vehicle[]>('/vehicles/').then(setVehiclesList).catch(() => { });
  }, []);

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return;

    if (window.L) {
      const map = window.L.map(mapRef.current).setView([10.0305, 105.7684], 15);
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);
      leafletMap.current = map;
    }
  }, []);

  // Update map markers when buses update
  const updateMarkers = (locations: BusLocation[]) => {
    if (!leafletMap.current || !window.L) return;

    locations.forEach((bus) => {
      const { vehicle_id, license_plate, latitude, longitude, speed = 0, status = 'in_progress' } = bus;

      const popupContent = `
        <div class="bus-popup">
          <h4>🚌 Xe ${license_plate || `#${vehicle_id}`}</h4>
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
    setBuses(defaultBuses);
    updateMarkers(defaultBuses);

    // Try WebSocket connection
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
        } catch (e) { }
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
          Kênh giám sát vị trí GPS trực tiếp {wsConnected ? '(Đã kết nối WebSocket)' : '(Chế độ mô phỏng / REST Polling)'}
        </div>
        <small style={{ opacity: 0.9 }}>Cập nhật mỗi 2 giây</small>
      </div>

      <div className="two-col">
        <div ref={mapRef} className="map-container" />

        <section className="panel" style={{ height: 520, overflowY: 'auto' }}>
          <h2>Danh sách xe buýt ({buses.length})</h2>
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
                    <strong style={{ color: '#087b7c' }}>🚌 {bus.license_plate || matchedVeh?.license_plate || `Xe #${bus.vehicle_id}`}</strong>
                    <span className={`bus-status-tag ${bus.status || 'in_progress'}`}>
                      {bus.status === 'in_progress' ? 'Đang chạy' : 'Đang dừng'}
                    </span>
                  </div>
                  <small style={{ color: '#65777d', display: 'block', marginTop: 4 }}>
                    Tài xế: {matchedVeh?.driver?.full_name || matchedVeh?.driver?.username || 'Đang phân công'}
                  </small>
                  <small style={{ color: '#087b7c', display: 'block', marginTop: 2 }}>
                    Tốc độ: {bus.speed ?? 0} km/h • Click để xem vị trí
                  </small>
                </article>
              );
            })}
          </div>
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
    api.get<User[]>('/users/').then((users) => setDrivers(users.filter((u) => u.role === 'driver'))).catch(() => { });
  };

  useEffect(() => {
    void load();
  }, []);

  const add = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    try {
      await api.post('/vehicles/', { license_plate: f.get('plate'), capacity: Number(f.get('capacity')) });
      void load();
      form.reset();
    } catch (err) {
      setError((err as Error).message);
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
        heads={['Biển số', 'Sức chứa', 'Trạng thái', 'Tài xế phân công', 'Thao tác']}
        rows={items.map((v) => {
          const meta = VEHICLE_STATUS_META[v.status || 'idle'];
          return (
            <tr key={v.id}>
              <td>
                <b>{v.license_plate}</b>
              </td>
              <td>{v.capacity} chỗ</td>
              <td>
                <span className="badge" style={{ background: meta.bg, color: meta.color }}>
                  {meta.label}
                </span>
              </td>
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
          );
        })}
      />
    </Page>
  );
}

function extractDetail(data: any): string {
  if (!data) return 'Đã xảy ra lỗi không xác định.';
  if (typeof data === 'string') return data;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
  }
  if (typeof data.message === 'string') return data.message;
  return JSON.stringify(data);
}

function Users({ currentUserId }: { currentUserId?: number }) {
  const [items, setItems] = useState<User[]>([]);
  const [roleFilter, setRoleFilter] = useState('all');
  const [error, setError] = useState('');

  const load = () => api.get<User[]>('/users/').then(setItems);

  useEffect(() => {
    void load();
  }, []);

  const changeRole = async (userId: number, newRole: string) => {
    if (userId === currentUserId) {
      alert('Bạn không thể tự đổi vai trò của chính tài khoản đang đăng nhập.');
      void load(); // reload để reset lại <select> về giá trị cũ trên UI
      return;
    }
    try {
      await api.put(`/users/${userId}/role`, { role: newRole });
      void load();
    } catch (e) {
      alert(getErrorMessage(e));
      void load();
    }
  };

  const addUser = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    setError('');
    try {
      await api.post('/users/', {
        username: f.get('username'),
        password: f.get('password'),
        full_name: f.get('full_name'),
        phone: f.get('phone'),
        role: f.get('role'),
      });
      void load();
      form.reset();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const deleteUser = async (userId: number, username: string) => {
    if (userId === currentUserId) {
      alert('Bạn không thể tự xóa chính tài khoản đang đăng nhập.');
      return;
    }
    if (!confirm(`Xóa tài khoản "${username}"? Hành động này không thể hoàn tác.`)) return;
    try {
      await api.delete(`/users/${userId}`);
      void load();
    } catch (e) {
      alert(getErrorMessage(e));
    }
  };

  const filtered = roleFilter === 'all' ? items : items.filter((u) => u.role === roleFilter);

  return (
    <Page title="Quản lý Tài khoản Người dùng">
      <section className="panel">
        <h2>Tạo tài khoản mới</h2>
        <form className="inline-form" onSubmit={addUser}>
          <input name="username" placeholder="Tên đăng nhập" required />
          <input name="password" type="password" placeholder="Mật khẩu" required />
          <input name="full_name" placeholder="Họ tên" />
          <input name="phone" placeholder="Số điện thoại" />
          <select name="role" defaultValue="passenger" required>
            <option value="passenger">Sinh viên</option>
            <option value="driver">Tài xế</option>
            <option value="admin">Admin</option>
          </select>
          <button>Tạo tài khoản</button>
        </form>
        {error && <div className="error">{error}</div>}
      </section>

      <div className="panel" style={{ display: 'flex', gap: 15, alignItems: 'center' }}>
        <span>Lọc theo vai trò:</span>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
          <option value="all">Tất cả người dùng ({items.length})</option>
          <option value="passenger">Sinh viên ({items.filter((u) => u.role === 'passenger').length})</option>
          <option value="driver">Tài xế ({items.filter((u) => u.role === 'driver').length})</option>
          <option value="admin">Quản trị viên ({items.filter((u) => u.role === 'admin').length})</option>
        </select>
      </div>

      <Table
        heads={['ID', 'Tài khoản', 'Họ tên', 'Điện thoại', 'Vai trò hiện tại', 'Thay đổi vai trò', 'Thao tác']}
        rows={filtered.map((u) => {
          const isSelf = u.id === currentUserId;
          return (
            <tr key={u.id} style={isSelf ? { background: 'var(--brand-light)' } : undefined}>
              <td>#{u.id}</td>
              <td>
                <b>{u.username}</b> {isSelf && <span className="badge" style={{ marginLeft: 6 }}>Bạn</span>}
              </td>
              <td>{u.full_name || '—'}</td>
              <td>{u.phone || '—'}</td>
              <td>
                <span className={`badge ${u.role}`}>{u.role === 'passenger' ? 'Sinh viên' : u.role === 'driver' ? 'Tài xế' : 'Quản trị viên'}</span>
              </td>
              <td>
                <select
                  value={u.role}
                  disabled={isSelf}
                  title={isSelf ? 'Không thể tự đổi vai trò của chính mình' : undefined}
                  onChange={(e) => changeRole(u.id, e.target.value)}
                  style={{ padding: '4px 8px', fontSize: 13 }}
                >
                  <option value="passenger">Sinh viên</option>
                  <option value="driver">Tài xế</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              <td>
                <button
                  className="danger-button"
                  disabled={isSelf}
                  title={isSelf ? 'Không thể tự xóa chính mình' : undefined}
                  onClick={() => deleteUser(u.id, u.username)}
                >
                  Xóa
                </button>
              </td>
            </tr>
          );
        })}
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

function RouteGenerator() {
  const [message, setMessage] = useState('');
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      const r: any = await api.post('/routes/generate', { date: f.get('date'), depot_location_id: Number(f.get('depot')) });
      setMessage(`Đã tạo tác vụ #${r.job_id}. Thuật toán Sweep + Tabu Search đang tự động phân bổ tuyến buýt.`);
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  return (
    <Page title="Tạo Tuyến buýt Tự động (Sweep + Tabu Search)">
      <section className="panel">
        <h2>Thuật toán Tối ưu Tuyến xe buýt Đưa đón CTU</h2>
        <p>Chọn trạm xuất phát depot và ngày chạy để tự động lập lịch trình và thứ tự trạm đón cho sinh viên.</p>
        <form className="inline-form" onSubmit={submit}>
          <input name="date" type="date" required />
          <input name="depot" type="number" min="1" defaultValue="1" placeholder="ID trạm depot" required />
          <button>Khởi tạo Tuyến</button>
        </form>
        {message && <p className="notice" style={{ marginTop: 15 }}>{message}</p>}
      </section>
    </Page>
  );
}

function Reports() {
  const [summary, setSummary] = useState<any>();
  const [avgRating, setAvgRating] = useState<number | null>(null);
  const [error, setError] = useState(false);

  const [trend, setTrend] = useState<{ date: string; revenue: number; ticket_count: number }[]>([]);
  const [trendLoading, setTrendLoading] = useState(true);
  const [range, setRange] = useState(7);

  useEffect(() => {
    setTrendLoading(true);
    api
      .get<any>(`/tickets/revenue-trend?days=${range}`)
      .then((res) => setTrend(res.data || []))
      .catch(() => setTrend([]))
      .finally(() => setTrendLoading(false));
  }, [range]);

  useEffect(() => {
    api
      .get<any>('/reports/summary')
      .then((data) => setSummary(data.summary))
      .catch(() => setError(true));

    // Tính rating trung bình thật từ danh sách reviews có sẵn
    api
      .get<any[]>('/reviews/')
      .then((reviews) => {
        if (reviews.length === 0) return setAvgRating(null);
        const avg = reviews.reduce((sum, r) => sum + (r.rating || 0), 0) / reviews.length;
        setAvgRating(Math.round(avg * 10) / 10);
      })
      .catch(() => setAvgRating(null));
  }, []);

  if (error) {
    return (
      <Page title="Báo cáo & Thống kê Vận hành">
        <div className="error">Không kết nối được dịch vụ báo cáo. Báo Leader kiểm tra API /reports/summary.</div>
      </Page>
    );
  }

  if (!summary) {
    return (
      <Page title="Báo cáo & Thống kê Vận hành">
        <p>Đang tải dữ liệu...</p>
      </Page>
    );
  }

  return (
    <Page title="Báo cáo & Thống kê Vận hành">
      <div className="stats">
        <Stat label="Xe trong hệ thống" value={summary.total_vehicles ?? '—'} icon="🚌" />
        <Stat label="Tuyến đã khởi tạo" value={summary.total_routes ?? '—'} icon="⌁" />
        <Stat label="Sinh viên đã đăng ký" value={summary.total_students ?? '—'} icon="♙" />
        <Stat
          label="Đánh giá trung bình"
          value={avgRating !== null ? `${avgRating}/5` : 'Chưa có đánh giá'}
          icon="⭐"
        />
      </div>

      <section className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Doanh thu & Vé bán</h2>
          <div style={{ display: 'flex', gap: 8 }}>
            {[7, 30].map((d) => (
              <button
                key={d}
                onClick={() => setRange(d)}
                style={{
                  padding: '6px 14px',
                  fontSize: 13,
                  borderRadius: 6,
                  border: '1px solid var(--border)',
                  background: range === d ? 'var(--brand)' : 'var(--surface)',
                  color: range === d ? '#fff' : 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
              >
                {d} ngày
              </button>
            ))}
          </div>
        </div>

        {trendLoading ? (
          <p>Đang tải dữ liệu doanh thu…</p>
        ) : trend.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)' }}>Chưa có dữ liệu vé trong khoảng thời gian này.</p>
        ) : (
          <div className="two-col">
            <div>
              <p style={{ margin: '0 0 4px', fontSize: 13, color: 'var(--text-secondary)' }}>
                Doanh thu {range} ngày —{' '}
                <b style={{ color: 'var(--text-primary)' }}>
                  {trend.reduce((sum, d) => sum + d.revenue, 0).toLocaleString('vi-VN')} đ
                </b>
              </p>
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend} margin={{ left: -20, right: 8 }}>
                    <CartesianGrid stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                    <YAxis
                      tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                      axisLine={false}
                      tickLine={false}
                      width={55}
                      tickFormatter={(v) => `${Math.round(v / 1000)}k`}
                    />
                    <Tooltip formatter={(v: number) => [`${v.toLocaleString('vi-VN')} đ`, 'Doanh thu']} />
                    <Line type="monotone" dataKey="revenue" stroke="#0b3d6b" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div>
              <p style={{ margin: '0 0 4px', fontSize: 13, color: 'var(--text-secondary)' }}>
                Số vé bán {range} ngày —{' '}
                <b style={{ color: 'var(--text-primary)' }}>
                  {trend.reduce((sum, d) => sum + d.ticket_count, 0)} vé
                </b>
              </p>
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trend} margin={{ left: -20, right: 8 }}>
                    <CartesianGrid stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={30} />
                    <Tooltip formatter={(v: number) => [`${v} vé`, 'Số vé']} />
                    <Bar dataKey="ticket_count" fill="#f0a202" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
      </section>
    </Page>
  );
}

function Settings() {
  const [price, setPrice] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get<any>('/settings/')
      .then((res) => {
        setPrice(res.ticket_price);
        setDraft(String(res.ticket_price));
      })
      .catch(() => setError('Không tải được giá vé hiện tại.'));
  }, []);

  const save = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const value = Number(draft);
    if (!value || value < 0) return;
    setSaving(true);
    setSaved(false);
    setError('');
    try {
      const res: any = await api.put('/settings/ticket-price', { ticket_price: value });
      setPrice(res.ticket_price);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Page title="Cài đặt Hệ thống">
      <section className="panel">
        <h2>Giá vé đồng giá toàn hệ thống</h2>
        <p style={{ color: '#708187', fontSize: 14, marginTop: 4 }}>
          Áp dụng cho mọi tuyến. Vé đã mua trước đó giữ nguyên giá tại thời điểm mua, không bị ảnh hưởng khi đổi giá.
        </p>

        {price !== null && (
          <p style={{ fontSize: 13, color: '#486069', marginTop: 10 }}>
            Giá hiện tại: <b>{price.toLocaleString('vi-VN')} đ</b>
          </p>
        )}

        <form className="inline-form" onSubmit={save} style={{ marginTop: 10 }}>
          <input
            type="number"
            min={0}
            step={1000}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Giá vé mới (đ)"
            required
          />
          <button disabled={saving}>{saving ? 'Đang lưu…' : 'Lưu giá vé'}</button>
        </form>

        {saved && (
          <p className="notice" style={{ marginTop: 12 }}>
            ✓ Đã cập nhật giá vé mới
          </p>
        )}
        {error && <div className="error">{error}</div>}
      </section>

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

function Tickets() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [routeFilter, setRouteFilter] = useState('all');

  useEffect(() => {
    setLoading(true);
    const query = routeFilter === 'all' ? '' : `?route_id=${routeFilter}`;
    api
      .get<Ticket[]>(`/tickets/${query}`)
      .then(setTickets)
      .catch(() => setTickets([]))
      .finally(() => setLoading(false));
  }, [routeFilter]);

  const availableRoutes = Array.from(
    new Set(tickets.map((t) => t.route_id).filter((id): id is number => !!id))
  ).sort((a, b) => a - b);

  return (
    <Page title="Quản lý Vé">
      <section className="panel table-wrap">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 4px 14px' }}>
          <h2 style={{ margin: 0 }}>
            Danh sách vé <span style={{ fontWeight: 400, color: '#708187' }}>({tickets.length})</span>
          </h2>
          <select
            value={routeFilter}
            onChange={(e) => setRouteFilter(e.target.value)}
            style={{ padding: '6px 10px', fontSize: 13 }}
          >
            <option value="all">Tất cả tuyến</option>
            {availableRoutes.map((id) => (
              <option key={id} value={id}>
                Tuyến #{id}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <p style={{ padding: 20, textAlign: 'center', color: '#708187' }}>Đang tải danh sách vé…</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Mã QR</th>
                <th>Tuyến</th>
                <th>Trạng thái</th>
                <th>Giá</th>
                <th>Ngày mua</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr key={t.id}>
                  <td>
                    <code>{t.qr_code}</code>
                  </td>
                  <td>{t.route_id ? `Tuyến #${t.route_id}` : '—'}</td>
                  <td>
                    <span className="badge">
                      {t.status === 'active' ? 'Còn hiệu lực' : t.status === 'used' ? 'Đã sử dụng' : 'Hết hạn'}
                    </span>
                  </td>
                  <td>{t.price.toLocaleString('vi-VN')} đ</td>
                  <td>{new Date(t.created_at).toLocaleDateString('vi-VN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading && tickets.length === 0 && (
          <p style={{ padding: 20, textAlign: 'center', color: '#708187' }}>Chưa có vé nào được bán.</p>
        )}
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