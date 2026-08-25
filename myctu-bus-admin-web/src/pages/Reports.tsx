import React, { useState, useEffect, useRef, FormEvent, ReactNode } from 'react';
import { NavLink, useNavigate, Routes, Route, Navigate } from 'react-router-dom';
import { api, auth, WS_URL } from '../services/api';
import { User, Vehicle, Incident, BusLocation, Location } from '../types';
import Page from '../components/Page';
import Stat from '../components/Stat';
import Table from '../components/Table';

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


export default Reports;
