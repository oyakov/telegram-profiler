import React, { useState } from 'react';
import useSWR from 'swr';
import { ChevronDown, Check, LayoutGrid, MessageCircle } from 'lucide-react';
import { getDatabase, setDatabase } from '../services/api';
import api from '../services/api';
import './TopBar.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const TopBar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentDb, setCurrentDb] = useState(getDatabase());
  const { data: telegramStatus } = useSWR('/api/telegram/auth/status', fetcher, { refreshInterval: 5000 });
  const { data: projectsData } = useSWR('/api/projects', fetcher);

  const projects = (projectsData || []).map((p: { name: string, db_name: string, description?: string }) => ({
    id: p.db_name,
    label: p.name,
    description: p.description
  }));

  // Ensure 'crm' is always available as a fallback if no projects are loaded
  if (projects.length === 0) {
    projects.push({ id: 'crm', label: '🇷🇸 Belgrade Intel', description: 'General intelligence' });
  }

  const handleSelect = (id: string) => {
    setDatabase(id);
    setCurrentDb(id);
    setIsOpen(false);
    window.location.reload(); // Hard reload to clear all SWR caches and reset context
  };

  return (
    <header className="top-bar">
      <div className="project-switcher-container">
        <button className="switcher-btn" onClick={() => setIsOpen(!isOpen)}>
          <LayoutGrid size={18} className="text-secondary" />
          <span className="current-project-label">
            {projects.find((p: { id: string, label: string }) => p.id === currentDb)?.label || currentDb}
          </span>
          <ChevronDown size={16} className={`chevron ${isOpen ? 'open' : ''}`} />
        </button>

        {isOpen && (
          <div className="project-menu serpent-card">
            {projects.map((project: { id: string, label: string, description?: string }) => (
              <div 
                key={project.id} 
                className={`project-item ${currentDb === project.id ? 'active' : ''}`}
                onClick={() => handleSelect(project.id)}
              >
                <div className="project-item-info">
                  <span className="project-label">{project.label}</span>
                  <span className="project-desc">{project.description}</span>
                </div>
                {currentDb === project.id && <Check size={16} className="check-icon" />}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="header-right">
        {telegramStatus?.authorized && (
          <div className="telegram-status" title="Telegram connected">
            <MessageCircle size={16} style={{ color: '#10b981' }} />
            <span className="status-text" style={{ color: '#10b981' }}>Telegram</span>
            <span className="pulse-dot" style={{ backgroundColor: '#10b981' }}></span>
          </div>
        )}
        <div className="search-status">
          <span className="pulse-dot"></span>
          <span className="status-text">System Online</span>
        </div>
        <div className="user-profile">
          <div className="avatar">O</div>
        </div>
      </div>
    </header>
  );
};

export default TopBar;
