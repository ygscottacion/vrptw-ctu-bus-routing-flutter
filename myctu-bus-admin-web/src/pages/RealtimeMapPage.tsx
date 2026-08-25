import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

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


export default RealtimeMapPage;
