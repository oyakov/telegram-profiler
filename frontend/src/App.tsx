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
import PersonalContacts from './pages/PersonalContacts';
import Settings from './pages/Settings';
import Projects from './pages/Projects';
import Audit from './pages/Audit';
import './App.css';

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
    </Router>
  );
};

export default App;
