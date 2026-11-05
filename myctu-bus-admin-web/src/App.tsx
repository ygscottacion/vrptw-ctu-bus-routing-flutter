import { FormEvent, ReactNode, useEffect, useRef, useState } from 'react';
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import { api, setAuthFailureHandler } from './services/api';
import { supabase } from './services/supabase';

type User = { id: string; role: string; email?: string | null; full_name?: string | null; phone?: string | null; username?: string };
type Vehicle = { id: string; license_plate: string; capacity: number; driver?: User; driver_id?: string };
type RouteDriverOption = { id: string; full_name?: string | null; phone?: string | null; vehicle_id: string; license_plate: string; capacity: number; busy: boolean };
type Incident = { id: string; title: string; description?: string; status: string; reported_at: string; driver?: User };
type LocationItem = { id: string; code?: string; name: string; latitude: number; longitude: number };
type RouteStop = { id: string; route_id: string; location_id: string; stop_order: number; arrival_time?: string; departure_time?: string; time_window_start?: string; time_window_end?: string; location?: LocationItem };
type RouteItem = {
  id: string;
  route_job_id?: string;
  service_date: string;
  session_id: string;
  trip_type: string;
  vehicle_id?: string;
  status: 'pending' | 'approved' | 'rejected' | 'in_progress' | 'completed';
  total_distance: number;
  driving_duration_minutes?: number;
  waiting_duration_minutes?: number;
  service_duration_minutes?: number;
  departure_time?: string;
  estimated_school_arrival_time?: string;
  stops: RouteStop[];
  passenger_count?: number;
  vehicle?: Vehicle;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
};

declare global {
  interface Window {
    goongjs: any;
  }
}

const menu = [
  ['/dashboard', '▦', 'Tổng quan'],
  ['/map', '📍', 'Bản đồ tuyến xe'],
  ['/vehicles', '🚌', 'Xe buýt'],
  ['/routes', '⌁', 'Tuyến đường & Duyệt'],
  ['/users', '♙', 'Người dùng'],
  ['/incidents', '⚠', 'Sự cố']
];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setAuthFailureHandler(() => setUser(null));

    const initSession = async () => {
      try {
        const {
          data: { session }
        } = await supabase.auth.getSession();
        if (!session) {
          setUser(null);
          setLoading(false);
          return;
        }
        const me = await api.get<User>('/auth/me');
        if (me.role !== 'admin') {
          await supabase.auth.signOut();
          setUser(null);
        } else {
          setUser(me);
        }
      } catch {
        await supabase.auth.signOut();
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    initSession();

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        setUser(null);
      }
    });

    return () => {
      subscription.unsubscribe();
      setAuthFailureHandler(null);
    };
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
              onLogout={async () => {
                await supabase.auth.signOut();
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
    const email = String(f.get('email') || '').trim();
    const password = String(f.get('password') || '');

    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({ email, password });
      if (authError) {
        if (authError.message.includes('Invalid login credentials')) {
          throw new Error('Sai email hoặc mật khẩu.');
        }
        if (authError.message.includes('Email not confirmed')) {
          throw new Error('Email chưa được xác nhận. Vui lòng kiểm tra hộp thư.');
        }
        throw new Error(authError.message || 'Đăng nhập thất bại.');
      }

      if (!data.session) {
        throw new Error('Không thể khởi tạo phiên làm việc.');
      }

      const userProfile = await api.get<User>('/auth/me');
      if (userProfile.role !== 'admin') {
        await supabase.auth.signOut();
        throw new Error('Tài khoản không có quyền truy cập trang quản trị.');
      }

      onSuccess(userProfile);
    } catch (err) {
      if (err instanceof Error && (err.message.includes('Failed to fetch') || err.message.includes('fetch'))) {
        setError('Không thể kết nối đến máy chủ Backend (http://localhost:8000) hoặc Supabase. Vui lòng kiểm tra server Backend đã chạy chưa.');
      } else {
        setError(err instanceof Error ? err.message : 'Đăng nhập thất bại');
      }
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
          Email
          <input name="email" type="email" required autoFocus placeholder="admin@test.example.com" autoComplete="email" />
        </label>
        <label>
          Mật khẩu
          <input name="password" type="password" required autoComplete="current-password" />
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
          onClick={async () => {
            await onLogout();
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
            {user.full_name || user.email || user.username || 'Admin'}
            <span>Quản trị viên</span>
          </div>
        </header>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/map" element={<GeneratedRoutesMapPage />} />
          <Route path="/vehicles" element={<Vehicles />} />
          <Route path="/routes" element={<RouteGenerator />} />
          <Route path="/users" element={<Users />} />
          <Route path="/incidents" element={<Incidents />} />
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
            Xem các tuyến xe đã được sinh theo ngày, đối chiếu thứ tự trạm và chọn từng tuyến để kiểm tra chi tiết trên bản đồ.
          </p>
          <div style={{ marginTop: 15 }}>
            <NavLink to="/map" className="badge" style={{ textDecoration: 'none', padding: '8px 14px', fontSize: 13 }}>
              📍 Mở bản đồ tuyến xe →
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

function GeneratedRoutesMapPage() {
  const mapRef = useRef<HTMLDivElement>(null);
  const goongMap = useRef<any>(null);
  const mapLoadedRef = useRef(false);
  const renderRevision = useRef(0);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState('');
  const [routes, setRoutes] = useState<RouteItem[]>([]);
  const [selectedDate, setSelectedDate] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  });
  const [selectedRouteId, setSelectedRouteId] = useState('all');
  const [loadingRoutes, setLoadingRoutes] = useState(true);
  const [routesError, setRoutesError] = useState('');

  useEffect(() => {
    if (!mapRef.current || goongMap.current) return;
    if (!window.goongjs) {
      setMapError('Không tải được Goong Maps SDK. Hãy kiểm tra kết nối mạng rồi tải lại trang.');
      return;
    }
    if (!window.goongjs.supported()) {
      setMapError('Trình duyệt hiện tại không hỗ trợ Goong Maps/WebGL.');
      return;
    }
    const goongTileKey = (import.meta as any).env?.VITE_GOONG_MAPTILES_KEY || 'rwZKp27qLAlPcckb3HOe3E4JwiOaR54wPiW9hwJx';
    window.goongjs.accessToken = goongTileKey;
    const map = new window.goongjs.Map({
      container: mapRef.current,
      style: 'https://tiles.goong.io/assets/goong_map_web.json',
      center: [105.7684, 10.0305],
      zoom: 13
    });
    goongMap.current = map;
    map.on('load', () => {
      map.addSource('generated-route-lines', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });
      map.addLayer({
        id: 'generated-route-lines',
        type: 'line',
        source: 'generated-route-lines',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': ['get', 'color'], 'line-width': 5, 'line-opacity': 0.9 }
      });
      map.addSource('generated-route-stops', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });
      map.addLayer({
        id: 'generated-route-stops',
        type: 'circle',
        source: 'generated-route-stops',
        paint: {
          'circle-radius': ['get', 'radius'],
          'circle-color': ['get', 'color'],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2
        }
      });
      map.on('click', 'generated-route-stops', (event: any) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const [lng, lat] = feature.geometry.coordinates;
        const properties = feature.properties || {};
        const popup = document.createElement('div');
        const name = document.createElement('strong');
        name.textContent = properties.name || 'Trạm xe buýt';
        const route = document.createElement('div');
        route.textContent = properties.route || '';
        const order = document.createElement('small');
        order.textContent = `Thứ tự trạm: ${properties.order ?? ''}`;
        popup.append(name, route, order);
        new window.goongjs.Popup({ closeButton: true })
          .setLngLat([lng, lat])
          .setDOMContent(popup)
          .addTo(map);
      });
      map.on('mouseenter', 'generated-route-stops', () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', 'generated-route-stops', () => { map.getCanvas().style.cursor = ''; });
      mapLoadedRef.current = true;
      setMapError('');
      setMapReady(true);
    });
    map.on('error', (event: any) => {
      if (!mapLoadedRef.current) {
        setMapError(event.error?.message || 'Goong Maps không tải được bản đồ. Hãy kiểm tra MapTiles API key và domain trên Goong Console.');
      }
    });
    return () => {
      map.remove();
      goongMap.current = null;
      mapLoadedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadingRoutes(true);
    setRoutesError('');
    setRoutes([]);
    setSelectedRouteId('all');
    api.get<RouteItem[]>(`/routes/?service_date=${encodeURIComponent(selectedDate)}`)
      .then((items) => {
        if (!cancelled) setRoutes(items);
      })
      .catch((error: Error) => {
        if (!cancelled) setRoutesError(error.message || 'Không tải được danh sách tuyến.');
      })
      .finally(() => {
        if (!cancelled) setLoadingRoutes(false);
      });
    return () => { cancelled = true; };
  }, [selectedDate]);

  useEffect(() => {
    const map = goongMap.current;
    if (!map || !mapReady || !mapLoadedRef.current || loadingRoutes) return;

    const revision = ++renderRevision.current;
    const visibleRoutes = selectedRouteId === 'all'
      ? routes
      : routes.filter((route) => route.id === selectedRouteId);
    const palette = ['#087b7c', '#e64b3c', '#6b58b8', '#d58a12', '#27804b', '#2873b8', '#bd4d83'];
    const allCoordinates: [number, number][] = [];
    const stopFeatures: any[] = [];
    const lineFeatures: any[] = [];

    const routeLabel = (route: RouteItem) => {
      const direction = route.trip_type === 'pickup' ? 'Chiều đi' : 'Chiều về';
      return `CT-${route.id.slice(0, 8).toUpperCase()} • ${direction} • ${route.session_id}`;
    };

    visibleRoutes.forEach((route, routeIndex) => {
      const color = palette[routeIndex % palette.length];
      const orderedStops = [...(route.stops || [])].sort((a, b) => a.stop_order - b.stop_order);
      const coordinates = orderedStops.flatMap((stop) => {
        const lat = Number(stop.location?.latitude);
        const lng = Number(stop.location?.longitude);
        return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180
          ? [[lat, lng] as [number, number]]
          : [];
      });
      allCoordinates.push(...coordinates);

      orderedStops.forEach((stop) => {
        const lat = Number(stop.location?.latitude);
        const lng = Number(stop.location?.longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return;
        stopFeatures.push({
          type: 'Feature',
          properties: {
            name: stop.location?.name || `Trạm ${stop.stop_order}`,
            route: routeLabel(route),
            order: stop.stop_order,
            color,
            radius: selectedRouteId === 'all' ? 7 : 9
          },
          geometry: { type: 'Point', coordinates: [lng, lat] }
        });
      });

      if (coordinates.length > 1) {
        const waypoints = coordinates.map(([lat, lng]) => `${lat},${lng}`).join(';');
        api.get<{ routed?: boolean; points?: number[][] }>(`/routes/polyline?waypoints=${encodeURIComponent(waypoints)}`)
          .then((result) => {
            if (revision !== renderRevision.current || result.routed !== true || !Array.isArray(result.points)) return;
            const path = result.points
              .filter((point) => Array.isArray(point) && point.length >= 2 && Number.isFinite(point[0]) && Number.isFinite(point[1]))
              .map(([lat, lng]) => [lng, lat] as [number, number]);
            if (path.length < 2) return;
            lineFeatures.push({
              type: 'Feature',
              properties: { color },
              geometry: { type: 'LineString', coordinates: path }
            });
            map.getSource('generated-route-lines')?.setData({ type: 'FeatureCollection', features: [...lineFeatures] });
          })
          .catch(() => {});
      }
    });

    map.getSource('generated-route-stops')?.setData({ type: 'FeatureCollection', features: stopFeatures });
    if (allCoordinates.length > 0) {
      const bounds = new window.goongjs.LngLatBounds();
      allCoordinates.forEach(([lat, lng]) => bounds.extend([lng, lat]));
      map.fitBounds(bounds, { padding: 28, maxZoom: 15 });
    }
    map.getSource('generated-route-lines')?.setData({ type: 'FeatureCollection', features: [] });
  }, [routes, selectedRouteId, loadingRoutes, mapReady]);

  const visibleRoutes = selectedRouteId === 'all'
    ? routes
    : routes.filter((route) => route.id === selectedRouteId);
  const describeRoute = (route: RouteItem) => {
    const direction = route.trip_type === 'pickup' ? 'Chiều đi' : 'Chiều về';
    return `CT-${route.id.slice(0, 8).toUpperCase()} • ${direction} • ${route.session_id}`;
  };

  return (
    <Page title="Bản đồ Tuyến xe đã sinh">
      <div className="live-feed-bar" style={{ flexWrap: 'wrap', gap: 14 }}>
        <strong>Chọn ngày và tuyến đã được sinh</strong>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            Ngày:
            <input type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            Tuyến:
            <select value={selectedRouteId} onChange={(event) => setSelectedRouteId(event.target.value)} disabled={routes.length === 0}>
              <option value="all">Tất cả tuyến trong ngày ({routes.length})</option>
              {routes.map((route) => <option key={route.id} value={route.id}>{describeRoute(route)}</option>)}
            </select>
          </label>
        </div>
      </div>

      <div className="two-col">
        <div className="map-container" style={{ position: 'relative' }}>
          <div ref={mapRef} style={{ position: 'absolute', inset: 0 }} />
          {mapError && <div className="map-error">{mapError}</div>}
        </div>

        <section className="panel" style={{ height: 520, overflowY: 'auto' }}>
          <h2>{selectedRouteId === 'all' ? `Các tuyến trong ngày (${visibleRoutes.length})` : 'Thông tin tuyến đang chọn'}</h2>
          {loadingRoutes ? (
            <p style={{ color: '#708187', fontSize: 14 }}>Đang tải các tuyến trong ngày...</p>
          ) : routesError ? (
            <p style={{ color: '#b42318', fontSize: 14 }}>{routesError}</p>
          ) : visibleRoutes.length === 0 ? (
            <p style={{ color: '#708187', fontSize: 14 }}>Ngày này chưa có tuyến nào được sinh.</p>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {visibleRoutes.map((route) => {
                const selected = selectedRouteId === route.id;
                const stops = [...(route.stops || [])].sort((a, b) => a.stop_order - b.stop_order);
                return (
                  <article
                    key={route.id}
                    onClick={() => setSelectedRouteId(route.id)}
                    style={{
                      padding: 12,
                      borderRadius: 8,
                      border: selected ? '1px solid #087b7c' : '1px solid #e2eaec',
                      cursor: 'pointer',
                      background: selected ? '#effafa' : '#fcfdfe'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                      <strong style={{ color: '#087b7c' }}>{describeRoute(route)}</strong>
                      <span className={`bus-status-tag ${route.status === 'in_progress' ? 'active' : 'idle'}`}>
                        {route.status === 'in_progress' ? 'Đang chạy' : route.status === 'completed' ? 'Hoàn thành' : route.status === 'approved' ? 'Đã duyệt' : route.status === 'rejected' ? 'Từ chối' : 'Chờ duyệt'}
                      </span>
                    </div>
                    <small style={{ color: '#65777d', display: 'block', marginTop: 4 }}>
                      Xe: {route.vehicle?.license_plate || 'Chưa phân công'} • {stops.length} trạm
                    </small>
                    <small style={{ color: '#087b7c', display: 'block', marginTop: 2 }}>
                      {stops[0]?.location?.name || 'Điểm đầu chưa rõ'} → {stops[stops.length - 1]?.location?.name || 'Điểm cuối chưa rõ'}
                    </small>
                  </article>
                );
              })}
            </div>
          )}
          {selectedRouteId !== 'all' && routes.length > 0 && (
            <button type="button" style={{ marginTop: 12 }} onClick={() => setSelectedRouteId('all')}>
              Hiển thị tất cả tuyến
            </button>
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
                    {d.full_name || d.email || d.username || d.id}
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
              <b>{u.email || u.username || u.id}</b>
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
  const [driverOptions, setDriverOptions] = useState<Record<string, RouteDriverOption[]>>({});
  const [selectedDrivers, setSelectedDrivers] = useState<Record<string, string>>({});
  const [loadingDrivers, setLoadingDrivers] = useState<string | null>(null);

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
      const normalizedStatus = job.status.toUpperCase();
      setJobStatus({ id: jobId, status: normalizedStatus, message: job.error_message });
      if (normalizedStatus === 'QUEUED' || normalizedStatus === 'RUNNING') {
        setTimeout(() => pollJobStatus(jobId), 2000);
      } else {
        setSubmitting(false);
        if (normalizedStatus === 'SUCCEEDED') {
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
      setJobStatus({ id: res.job_id, status: res.status.toUpperCase() });
      pollJobStatus(res.job_id);
    } catch (e) {
      setJobStatus({ id: '', status: 'FAILED', message: (e as Error).message });
      setSubmitting(false);
    }
  };

  const loadDriverOptions = async (routeId: string) => {
    setLoadingDrivers(routeId);
    try {
      const options = await api.get<RouteDriverOption[]>(`/routes/${routeId}/drivers`);
      setDriverOptions((current) => ({ ...current, [routeId]: options }));
      setSelectedDrivers((current) => ({ ...current, [routeId]: current[routeId] || '' }));
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setLoadingDrivers(null);
    }
  };

  const approveRoute = async (routeId: string) => {
    const driverId = selectedDrivers[routeId];
    if (!driverId) {
      alert('Chọn một tài xế đang rảnh trước khi duyệt tuyến.');
      return;
    }
    try {
      await api.post(`/routes/${routeId}/approve`, { driver_id: driverId });
      void loadRoutes();
      setDriverOptions((current) => { const next = { ...current }; delete next[routeId]; return next; });
    } catch (e) {
      alert((e as Error).message);
      void loadDriverOptions(routeId);
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
          heads={['Mã / ID Tuyến', 'Ngày chạy', 'Ca / Chiều', 'Tài xế', 'Số SV đón', 'Quãng đường', 'Thời gian chạy', 'Trạng thái', 'Thao tác duyệt / Manifest']}
          rows={routes.map((r) => (
            <tr key={r.id}>
              <td>
                <b style={{ color: '#087b7c' }}>CT-{r.id.slice(0, 8).toUpperCase()}</b>
              </td>
              <td>{r.service_date}</td>
              <td>
                {r.session_id} • {r.trip_type === 'pickup' ? 'Đón' : 'Trả'}
              </td>
              <td>
                {r.status === 'pending'
                  ? 'Chưa chọn'
                  : r.vehicle?.driver?.full_name || r.vehicle?.driver?.phone || 'Chưa có tài xế'}
                {r.status !== 'pending' && r.vehicle?.driver && <small style={{ display: 'block', color: '#667085' }}>{r.vehicle.license_plate}</small>}
                {r.status === 'pending' && (
                  <div style={{ marginTop: 6 }}>
                    {!driverOptions[r.id] ? (
                      <button type="button" style={{ fontSize: 12, padding: '4px 8px' }} disabled={loadingDrivers === r.id} onClick={() => void loadDriverOptions(r.id)}>
                        {loadingDrivers === r.id ? 'Đang tải…' : 'Chọn tài xế'}
                      </button>
                    ) : (
                      <select
                        aria-label={`Chọn tài xế cho tuyến ${r.id.slice(0, 8)}`}
                        value={selectedDrivers[r.id] || ''}
                        onChange={(event) => setSelectedDrivers((current) => ({ ...current, [r.id]: event.target.value }))}
                        style={{ maxWidth: 190, fontSize: 12 }}
                      >
                        <option value="">-- Chọn tài xế --</option>
                        {driverOptions[r.id].map((driver) => (
                          <option key={driver.id} value={driver.id} disabled={driver.busy}>
                            {driver.full_name || driver.phone || driver.id.slice(0, 8)} · {driver.license_plate}{driver.busy ? ' · Tài xế đang bận' : ''}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                )}
              </td>
              <td>{r.passenger_count ?? 0} sinh viên</td>
              <td>{r.total_distance?.toFixed(1) ?? '0.0'} km</td>
              <td>{r.driving_duration_minutes != null ? `${r.driving_duration_minutes.toFixed(1)} phút` : '—'}</td>
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
                    <button style={{ fontSize: 12, padding: '4px 8px', background: '#087b7c' }} disabled={!selectedDrivers[r.id]} onClick={() => approveRoute(r.id)}>
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
            <p style={{ color: '#666', fontSize: 13 }}>
              Xuất phát: <b>{selectedRouteForStops.departure_time ? new Date(selectedRouteForStops.departure_time).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : '—'}</b>
              {' • '}Về trường: <b>{selectedRouteForStops.estimated_school_arrival_time ? new Date(selectedRouteForStops.estimated_school_arrival_time).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : '—'}</b>
              {' • '}Thời gian xe chạy: <b>{selectedRouteForStops.driving_duration_minutes?.toFixed(1) ?? '—'} phút</b>
              {' • '}Chờ: <b>{selectedRouteForStops.waiting_duration_minutes?.toFixed(1) ?? '—'} phút</b>
              {' • '}Đón khách: <b>{selectedRouteForStops.service_duration_minutes?.toFixed(1) ?? '—'} phút</b>
            </p>

            <table style={{ width: '100%', marginTop: 15, borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f5f5f5', textAlign: 'left' }}>
                  <th style={{ padding: 8 }}>STT</th>
                  <th style={{ padding: 8 }}>Mã trạm</th>
                  <th style={{ padding: 8 }}>Tên trạm dừng</th>
                  <th style={{ padding: 8 }}>Dự kiến đến</th>
                  <th style={{ padding: 8 }}>Khung đón</th>
                  <th style={{ padding: 8 }}>Đón xong / rời trạm</th>
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
                      <td style={{ padding: 8 }}>
                        {stop.time_window_start && stop.time_window_end
                          ? `${new Date(stop.time_window_start).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}–${new Date(stop.time_window_end).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`
                          : '—'}
                      </td>
                      <td style={{ padding: 8 }}>
                        {stop.departure_time ? new Date(stop.departure_time).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : '—'}
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
