import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmProvider } from './context/ConfirmContext';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';

// Lazy load page components
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Tracking = lazy(() => import('./pages/Tracking'));
const Search = lazy(() => import('./pages/Search'));
const Monitoring = lazy(() => import('./pages/Monitoring'));
const Leads = lazy(() => import('./pages/Leads'));
const Campaigns = lazy(() => import('./pages/Campaigns'));
const Contacts = lazy(() => import('./pages/Contacts'));
const PersonalContacts = lazy(() => import('./pages/PersonalContacts'));
const Settings = lazy(() => import('./pages/Settings'));
const Audit = lazy(() => import('./pages/Audit'));

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

  return (
    <Suspense fallback={<LoadingScreen />}>
      {!isAuthenticated ? (
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="*"
            element={<Navigate to="/login" state={{ from: location.pathname }} replace />}
          />
        </Routes>
      ) : (
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
      )}
    </Suspense>
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
