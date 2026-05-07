import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import Dashboard from './pages/Dashboard';
import Tracking from './pages/Tracking';
import Search from './pages/Search';
import Monitoring from './pages/Monitoring';
import Leads from './pages/Leads';
import Contacts from './pages/Contacts';
import './App.css';

// Placeholder components for pages
const Settings = () => <div className="page-content"><h1>Настройки</h1><p>Контент в разработке...</p></div>;

const App: React.FC = () => {
  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <TopBar />
          <div className="scroll-area">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/tracking" element={<Tracking />} />
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/search" element={<Search />} />
              <Route path="/leads" element={<Leads />} />
              <Route path="/contacts" element={<Contacts />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
};

export default App;
