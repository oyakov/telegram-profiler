import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Target, 
  Activity, 
  Search, 
  Users, 
  Settings, 
  Database,
  BrainCircuit
} from 'lucide-react';
import './Sidebar.css';

const Sidebar: React.FC = () => {
  const navItems = [
    { name: 'Дашборд', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Проекты', path: '/projects', icon: <Database size={20} /> },
    { name: 'Трекинг', path: '/tracking', icon: <Target size={20} /> },
    { name: 'AI Мониторинг', path: '/monitoring', icon: <Activity size={20} /> },
    { name: 'Поиск и AI', path: '/search', icon: <Search size={20} /> },
    { name: 'Лиды', path: '/leads', icon: <BrainCircuit size={20} /> },
    { name: 'Контакты', path: '/contacts', icon: <Users size={20} /> },
    { name: 'Настройки', path: '/settings', icon: <Settings size={20} /> },
  ];

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
        <div className="db-indicator">
          <Database size={16} />
          <span>Active: {localStorage.getItem('selected_db') || 'crm'}</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
