import React from 'react';
import './Dashboard.css';
import Dashboard from './pages/Dashboard';
const Dashboard = () => {
  return (
    <div className="dashboard">
      <h2 className="page-title">Dashboard</h2>
      
      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#4caf50' }}>📦</div>
          <div className="stat-content">
            <h3>Tổng sản phẩm</h3>
            <p className="stat-value">0</p>
            <p className="stat-change positive">+0% so với tháng trước</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#2196f3' }}>📈</div>
          <div className="stat-content">
            <h3>Dự báo hoàn thành</h3>
            <p className="stat-value">0</p>
            <p className="stat-change positive">+0% so với tuần trước</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ff9800' }}>🎯</div>
          <div className="stat-content">
            <h3>Độ chính xác trung bình</h3>
            <p className="stat-value">0%</p>
            <p className="stat-change neutral">Không đổi</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#f44336' }}>⚠️</div>
          <div className="stat-content">
            <h3>Cảnh báo tồn kho</h3>
            <p className="stat-value">0</p>
            <p className="stat-change negative">-0 mục cần xử lý</p>
          </div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="card">
          <h3>Xu hướng dự báo gần đây</h3>
          <p className="text-secondary">Chưa có dữ liệu</p>
        </div>

        <div className="card">
          <h3>Sản phẩm được dự báo nhiều nhất</h3>
          <p className="text-secondary">Chưa có dữ liệu</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
