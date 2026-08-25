import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';

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

export default Table;
