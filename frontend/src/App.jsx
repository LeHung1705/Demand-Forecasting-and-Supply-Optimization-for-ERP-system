import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Layout
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import Footer from './components/layout/Footer';

// Pages
import Dashboard from './pages/DashboardPage';
import ProductManagement from './pages/ProductManagement';
import Forecasting from './pages/Forecasting';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import DemandPlanning from './pages/DemandPlanning';
import OptimizationDashboard from './pages/OptimizationDashboard';

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
        <DashboardProvider>
          <Router>
            <div className="flex h-screen bg-gray-100">
              <Sidebar />
              <div className="flex-1 flex flex-col overflow-hidden">
                <Header />
                <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100 p-4">
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/products" element={<ProductManagement />} />
                    <Route path="/forecasting" element={<Forecasting />} />
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/planning" element={<DemandPlanning />} />
                    <Route path="/optimization" element={<OptimizationDashboard />} />
                    <Route path="/settings" element={<Settings />} />
                    {/* Fallback route */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </main>
                <Footer />
              </div>
            </div>
            <ToastContainer position="top-right" autoClose={3000} />
          </Router>
        </DashboardProvider>
      </AppProvider>
    </QueryClientProvider>
  );
}

export default App;
