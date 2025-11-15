import React from 'react';
import { useApp } from '../../context/AppContext';
import './Header.css';

const Header = () => {
  const { user, toggleSidebar, toggleTheme, theme } = useApp();

  return (
    <header className="header">
      <div className="header-left">
        <button className="menu-button" onClick={toggleSidebar}>
          ☰
        </button>
        <h1 className="header-title">Demand Forecasting</h1>
      </div>
      
      <div className="header-right">
        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
        
        <div className="user-info">
          <span className="user-name">{user?.name || 'Guest'}</span>
          <div className="user-avatar">
            {user?.name?.charAt(0) || 'G'}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
