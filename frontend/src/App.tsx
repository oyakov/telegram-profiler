import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import api from './services/api';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Tracking from './pages/Tracking';
import Search from './pages/Search';
import Monitoring from './pages/Monitoring';
import Leads from './pages/Leads';
import Contacts from './pages/Contacts';
import PersonalContacts from './pages/PersonalContacts';
import Settings from './pages/Settings';
import Projects from './pages/Projects';
import Audit from './pages/Audit';
import './App.css';

const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await api.get('/api/telegram/auth/status');
        setIsAuthenticated(response.data.authorized);
      } catch (err) {
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <Router>
      {isAuthenticated ? (
        <div className="app-container">
          <Sidebar />
          <main className="main-content">
            <TopBar />
            <div className="scroll-area">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/tracking" element={<Tracking />} />
                <Route path="/monitoring" element={<Monitoring />} />
                <Route path="/audit" element={<Audit />} />
                <Route path="/search" element={<Search />} />
                <Route path="/leads" element={<Leads />} />
                <Route path="/contacts" element={<Contacts />} />
                <Route path="/personal-contacts" element={<PersonalContacts />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </div>
          </main>
        </div>
      ) : (
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      )}
    </Router>
  );
};

export default App;
