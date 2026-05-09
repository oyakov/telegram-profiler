import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import useSWR from 'swr';
import { 
  User, 
  Folder, 
  Activity, 
  Search, 
  Users, 
  Settings, 
  Database,
  BrainCircuit,
  ChevronUp,
  Check,
  ClipboardList
} from 'lucide-react';
import { getDatabase, setDatabase } from '../services/api';
import api from '../services/api';
import './Sidebar.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Sidebar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentDb, setCurrentDb] = useState(getDatabase());
  const { data: projectsData } = useSWR('/api/projects', fetcher);

  const navItems = [
    { name: 'Профиль', path: '/', icon: <User size={20} /> },
    { name: 'Папки', path: '/tracking', icon: <Folder size={20} /> },
    { name: 'Данные', path: '/monitoring', icon: <Activity size={20} /> },
    { name: 'Аудит', path: '/audit', icon: <ClipboardList size={20} /> },
    { name: 'Поиск и AI', path: '/search', icon: <Search size={20} /> },
    { name: 'Лиды', path: '/leads', icon: <BrainCircuit size={20} /> },
    { name: 'Контакты', path: '/contacts', icon: <Users size={20} /> },
    { name: 'Личные Контакты', path: '/personal-contacts', icon: <Users size={20} /> },
    { name: 'Настройки', path: '/settings', icon: <Settings size={20} /> },
  ];

  const projects = (projectsData || []).map((p: { name: string, db_name: string, description?: string }) => ({
    id: p.db_name,
    label: p.name,
    description: p.description
  }));

  if (projects.length === 0) {
    projects.push({ id: 'crm', label: '🇷🇸 Belgrade Intel', description: 'General intelligence' });
  }

  const handleSelect = (id: string) => {
    setDatabase(id);
    setCurrentDb(id);
    setIsOpen(false);
    window.location.reload();
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Activity className="logo-icon" size={32} />
        <h2 className="text-gradient">Profiler</h2>
      </div>
      
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink 
            key={item.path} 
            to={item.path} 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-name">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="project-switcher">
          <button 
            className={`db-switcher-btn ${isOpen ? 'open' : ''}`} 
            onClick={() => setIsOpen(!isOpen)}
          >
            <div className="db-info">
              <Database size={18} className="db-icon" />
              <div className="db-text">
                <span className="db-label">Project</span>
                <span className="db-name">
                  {projects.find((p: any) => p.id === currentDb)?.label || currentDb}
                </span>
              </div>
            </div>
            <ChevronUp size={16} className={`chevron ${isOpen ? 'open' : ''}`} />
          </button>

          {isOpen && (
            <div className="db-menu serpent-card">
              <div className="db-menu-header">Switch Project</div>
              <div className="db-menu-list">
                {projects.map((project: any) => (
                  <div 
                    key={project.id} 
                    className={`db-menu-item ${currentDb === project.id ? 'active' : ''}`}
                    onClick={() => handleSelect(project.id)}
                  >
                    <div className="db-menu-item-info">
                      <span className="db-menu-label">{project.label}</span>
                      {project.description && (
                        <span className="db-menu-desc">{project.description}</span>
                      )}
                    </div>
                    {currentDb === project.id && <Check size={16} className="check-icon" />}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
