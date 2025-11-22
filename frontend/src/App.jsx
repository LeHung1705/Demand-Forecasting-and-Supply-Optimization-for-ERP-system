import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Layout
import Header from './components/layout/Header';   // ❗ BỎ .tsx
import Sidebar from './components/layout/Sidebar';
import Footer from './components/layout/Footer';

// Pages
import Dashboard from './pages/DashboardPage';
import Products from './pages/Products';
import Forecasting from './pages/Forecasting';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

// Context
import { AppProvider } from './context/AppContext';
import { DashboardProvider } from './hooks/useDashboardState';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppProvider>
        <Router>
          <DashboardProvider>
          <div className="app">
            <Header />
            <div className="app-container">
              <Sidebar />
              <main className="main-content">
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/products" element={<Products />} />
                  <Route path="/forecasting" element={<Forecasting />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </main>
            </div>
            <Footer />
            <ToastContainer
              position="top-right"
              autoClose={3000}
              hideProgressBar={false}
              newestOnTop
              closeOnClick
              rtl={false}
              pauseOnFocusLoss
              draggable
              pauseOnHover
            />
          </div>
          </DashboardProvider>
        </Router>
      </AppProvider>
    </QueryClientProvider>
  );
}

export default App;
