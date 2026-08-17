import { FormEvent, ReactNode, useEffect, useRef, useState } from 'react';
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import { api, auth, WS_URL } from './services/api';

type User = { id: number; username: string; full_name?: string; phone?: string; role: string };
type Vehicle = { id: number; license_plate: string; capacity: number; driver?: User; driver_id?: number };
type Incident = { id: number; title: string; description?: string; status: string; reported_at: string; driver?: User };
type BusLocation = { vehicle_id: number; license_plate?: string; latitude: number; longitude: number; speed?: number; status?: string };

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
    api.get<Vehicle[]>('/vehicles/').then(setVehiclesList).catch(() => {});
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
