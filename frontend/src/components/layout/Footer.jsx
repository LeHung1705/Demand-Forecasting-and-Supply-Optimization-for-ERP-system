import React from 'react';
import './Footer.css';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="footer-content">
        <p>&copy; {currentYear} Demand Forecasting System. All rights reserved.</p>
        <p>Version {process.env.REACT_APP_VERSION || '1.0.0'}</p>
      </div>
    </footer>
  );
};

export default Footer;
