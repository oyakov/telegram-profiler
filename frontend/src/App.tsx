import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmProvider } from './context/ConfirmContext';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Tracking from './pages/Tracking';
import Search from './pages/Search';
import Monitoring from './pages/Monitoring';
import Leads from './pages/Leads';
import Campaigns from './pages/Campaigns';
import Contacts from './pages/Contacts';
import PersonalContacts from './pages/PersonalContacts';
import Settings from './pages/Settings';
import Audit from './pages/Audit';
import './App.css';

const LoadingScreen: React.FC = () => (
  <div className="loading-screen">
    <div className="loading-spinner" />
    <p className="loading-text">Загрузка...</p>
  </div>
);

const AppRoutes: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <LoadingScreen />;

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="*"
          element={<Navigate to="/login" state={{ from: location.pathname }} replace />}
        />
      </Routes>
    );
  }

  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <TopBar />
        <div className="scroll-area">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tracking" element={<Tracking />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/search" element={<Search />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/personal-contacts" element={<PersonalContacts />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </main>
    </div>
  );
};

const App: React.FC = () => (
  <AuthProvider>
    <ToastProvider>
      <ConfirmProvider>
        <Router>
          <AppRoutes />
        </Router>
      </ConfirmProvider>
    </ToastProvider>
  </AuthProvider>
);

export default App;
