import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';
import Layout from '../components/Layout';

function Locations() {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<any>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedPos, setSelectedPos] = useState<{ lat: number; lng: number } | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const load = () => {
    api.get<Location[]>('/locations/').then(data => {
      setLocations(data);
    }).catch(e => setError(e.message));
  };

  useEffect(() => {
    load();
  }, []);

  const updateMarkers = (locs: Location[]) => {
    if (!leafletMap.current || !window.L) return;
    
    leafletMap.current.eachLayer((layer: any) => {
      if (layer instanceof window.L.Marker) {
        leafletMap.current.removeLayer(layer);
      }
    });

    locs.forEach(loc => {
      window.L.marker([loc.latitude, loc.longitude], {
        icon: window.L.divIcon({ html: '🚏', className: 'location-icon', iconSize: [24, 24] })
      })
      .addTo(leafletMap.current)
      .bindPopup(`<b>${loc.name}</b><br/>Demand: ${loc.demand || 0}`);
    });
    
    if (selectedPos) {
        window.L.marker([selectedPos.lat, selectedPos.lng], {
           icon: window.L.divIcon({ html: '📍', className: 'selected-icon', iconSize: [24, 24] })
        }).addTo(leafletMap.current).bindPopup('Vị trí đang chọn').openPopup();
    }
  };

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return;
    if (window.L) {
      const map = window.L.map(mapRef.current).setView([10.0305, 105.7684], 14);
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
      leafletMap.current = map;
      
      map.on('click', (e: any) => {
        const { lat, lng } = e.latlng;
        setSelectedPos({ lat, lng });
      });
      
      updateMarkers(locations);
    }
  }, []);
  
  useEffect(() => {
    if (leafletMap.current) updateMarkers(locations);
  }, [locations, selectedPos]);

  const addLocation = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedPos) {
      setError('Vui lòng click chọn vị trí trên bản đồ trước!');
      return;
    }
    const form = e.currentTarget;
    const f = new FormData(form);
    setLoading(true);
    setError('');
    
    try {
        const datePrefix = new Date().toISOString().split('T')[0];
        const tStart = f.get('time_window_start') ? `${datePrefix}T${f.get('time_window_start')}:00Z` : null;
        const tEnd = f.get('time_window_end') ? `${datePrefix}T${f.get('time_window_end')}:00Z` : null;

        await api.post('/locations/', {
            name: String(f.get('name')),
            latitude: selectedPos.lat,
            longitude: selectedPos.lng,
            demand: Number(f.get('demand')),
            time_window_start: tStart,
            time_window_end: tEnd
        });
      form.reset();
      setSelectedPos(null);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const deleteLocation = async (id: number) => {
    if (!confirm('Xóa trạm dừng này?')) return;
    try {
      await api.delete(`/locations/${id}`);
      load();
    } catch (e) {
      alert(`Lỗi khi xóa: ${(e as Error).message}\n(Có thể do trạm này đã được gán vào Tuyến xe nào đó)`);
    }
  };

  return (
    <Page title="Quản lý Trạm dừng & Điểm đón (Locations)">
      <div className="two-col">
        <div ref={mapRef} className="map-container" style={{ height: 500 }} />
        
        <section className="panel" style={{ height: 500, overflowY: 'auto' }}>
          <h2>Thêm Trạm Mới</h2>
          <p style={{ color: '#087b7c', fontSize: 14 }}>
            {selectedPos 
              ? `Đã chọn vị trí: ${selectedPos.lat.toFixed(4)}, ${selectedPos.lng.toFixed(4)}` 
              : '👉 Vui lòng click vào bản đồ bên cạnh để chọn vị trí.'}
          </p>
          
          <form style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 15 }} onSubmit={addLocation}>
            <label>
              Tên trạm dừng
              <input name="name" required placeholder="Ví dụ: Cổng A ĐH Cần Thơ" style={{ width: '100%', padding: 8, marginTop: 4 }}/>
            </label>
            <label>
              Nhu cầu dự kiến (Demand)
              <input name="demand" type="number" min="0" defaultValue="5" required style={{ width: '100%', padding: 8, marginTop: 4 }}/>
            </label>
            <div style={{ display: 'flex', gap: 10 }}>
              <label style={{ flex: 1 }}>
                Khung giờ phục vụ (Bắt đầu)
                <input name="time_window_start" type="time" style={{ width: '100%', padding: 8, marginTop: 4 }}/>
              </label>
              <label style={{ flex: 1 }}>
                Khung giờ phục vụ (Kết thúc)
                <input name="time_window_end" type="time" style={{ width: '100%', padding: 8, marginTop: 4 }}/>
              </label>
            </div>
            {error && <div className="error">{error}</div>}
            <button disabled={!selectedPos || loading} style={{ marginTop: 10, padding: 10 }}>
              {loading ? 'Đang thêm...' : 'Lưu Trạm Dừng'}
            </button>
          </form>

          <h3 style={{ marginTop: 30 }}>Danh sách trạm hiện tại ({locations.length})</h3>
          <ul style={{ paddingLeft: 20, fontSize: 14, color: '#444' }}>
             {locations.map(loc => (
               <li key={loc.id} style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee', paddingBottom: 8 }}>
                 <div>
                   <b>{loc.name}</b> <small>(Demand: {loc.demand})</small><br/>
                   <code style={{ fontSize: 11 }}>{loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)}</code>
                   {loc.time_window_start && <span style={{ marginLeft: 8, fontSize: 11, color: '#087b7c' }}>🕒 {loc.time_window_start} - {loc.time_window_end}</span>}
                 </div>
                 <button className="danger-button" style={{ padding: '4px 10px', fontSize: 12, height: 'fit-content' }} onClick={() => deleteLocation(loc.id)}>Xóa</button>
               </li>
             ))}
          </ul>
        </section>
      </div>
    </Page>
  );
}
export default Locations;
