import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

function RouteGenerator() {
  const [message, setMessage] = useState('');
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<any>(null);
  const routeLayer = useRef<any>(null);
  const [locations, setLocations] = useState<Location[]>([]);

  useEffect(() => {
    api.get<Location[]>('/locations/').then(setLocations).catch(() => {});
  }, []);

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return;
    if (window.L) {
      const map = window.L.map(mapRef.current).setView([10.0305, 105.7684], 14);
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
      leafletMap.current = map;
      routeLayer.current = window.L.layerGroup().addTo(map);
    }
  }, []);

  useEffect(() => {
    if (!leafletMap.current || !window.L || locations.length === 0) return;
    
    // Xóa các marker cũ ngoài marker của tuyến (nếu có logic phức tạp hơn, nên tách riêng layer)
    locations.forEach(loc => {
      window.L.marker([loc.latitude, loc.longitude], {
        icon: window.L.divIcon({ html: '🚏', className: 'location-icon', iconSize: [24, 24] })
      })
      .addTo(leafletMap.current)
      .bindPopup(`<b>${loc.name}</b><br/>ID: ${loc.id}`);
    });
  }, [locations]);

  const pollJobStatus = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const statusRes: any = await api.get(`/routes/generate/status/${jobId}`);
        if (statusRes.status === 'completed') {
          clearInterval(interval);
          setMessage(`✅ Khởi tạo thành công! Đã tạo ${statusRes.routes.length} tuyến xe.`);
          
          if (!leafletMap.current || !window.L) return;
          // Xóa các route layer cũ nếu có
          routeLayer.current.clearLayers();
          
          // Các màu cho từng tuyến
          const colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6'];
          
          statusRes.routes.forEach((route: any, index: number) => {
            if (route.stops && route.stops.length > 0) {
              const latlngs = route.stops
                  .filter((s: any) => s.location)
                  .map((s: any) => [s.location.latitude, s.location.longitude]);
              
              if (latlngs.length > 1) {
                const routeColor = colors[index % colors.length];
                
                // Gọi OSRM để lấy đường giao thông thực tế
                const coordsStr = latlngs.map((ll: any) => `${ll[1]},${ll[0]}`).join(';');
                const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${coordsStr}?overview=full&geometries=geojson`;
                
                fetch(osrmUrl)
                  .then(res => res.json())
                  .then(data => {
                    if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
                      window.L.geoJSON(data.routes[0].geometry, {
                        style: { color: routeColor, weight: 5, opacity: 0.8 }
                      }).addTo(routeLayer.current);
                    } else {
                      window.L.polyline(latlngs, { color: routeColor, weight: 5, opacity: 0.8, dashArray: '10, 10' }).addTo(routeLayer.current);
                    }
                  })
                  .catch(() => {
                    window.L.polyline(latlngs, { color: routeColor, weight: 5, opacity: 0.8 }).addTo(routeLayer.current);
                  });
              }
            }
          });
          
        } else if (statusRes.status === 'failed') {
          clearInterval(interval);
          setMessage(`❌ Lỗi: ${statusRes.error_message || 'Tạo tuyến thất bại'}`);
        }
      } catch (e) {
        clearInterval(interval);
        setMessage(`❌ Lỗi khi kiểm tra tiến độ: ${(e as Error).message}`);
      }
    }, 2000); // Check every 2 seconds
  };

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setMessage('⏳ Đang khởi tạo tuyến...');
    if (routeLayer.current) routeLayer.current.clearLayers(); // Clear old routes
    
    try {
      const r: any = await api.post('/routes/generate', { date: f.get('date'), depot_location_id: Number(f.get('depot')) });
      pollJobStatus(r.job_id);
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  return (
    <Page title="Tạo Tuyến buýt Tự động (Sweep + Tabu Search)">
      <div className="two-col">
        {/* Bản đồ rộng chiếm phần lớn */}
        <div ref={mapRef} className="map-container" style={{ height: 600 }} />
        
        <section className="panel" style={{ height: 600, overflowY: 'auto' }}>
          <h2>Thuật toán Tối ưu Tuyến xe buýt Đưa đón CTU</h2>
          <p>Chọn trạm xuất phát depot và ngày chạy để tự động lập lịch trình và thứ tự trạm đón cho sinh viên.</p>
          <form style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 15 }} onSubmit={submit}>
            <label>
              Ngày hoạt động
              <input name="date" type="date" required style={{ width: '100%', padding: 8, marginTop: 4 }}/>
            </label>
            <label>
              Trạm xuất phát (Depot)
              <select name="depot" required style={{ width: '100%', padding: 8, marginTop: 4 }}>
                <option value="">-- Chọn Trạm Depot --</option>
                {locations.map(loc => (
                  <option key={loc.id} value={loc.id}>{loc.name} (ID: {loc.id})</option>
                ))}
              </select>
            </label>
            <button style={{ marginTop: 10 }}>Khởi tạo Tuyến</button>
          </form>
          {message && <p className="notice" style={{ marginTop: 15, padding: 15, backgroundColor: '#e9f5f5', borderRadius: 8, color: '#005f56' }}>{message}</p>}
        </section>
      </div>
    </Page>
  );
}

export default RouteGenerator;
