import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity,
  Search,
  Users,
  Settings,
  BrainCircuit,
  ClipboardList,
  Send,
  BookUser,
} from 'lucide-react';
import './Sidebar.css';

const Sidebar: React.FC = () => {
  const navItems = [
    { name: 'Данные',            path: '/monitoring',         icon: <Activity size={20} /> },
    { name: 'Аудит',             path: '/audit',              icon: <ClipboardList size={20} /> },
    { name: 'Поиск и AI',        path: '/search',             icon: <Search size={20} /> },
    { name: 'Лиды',              path: '/leads',              icon: <BrainCircuit size={20} /> },
    { name: 'Рассылки',          path: '/campaigns',          icon: <Send size={20} /> },
    { name: 'Контакты',          path: '/contacts',           icon: <Users size={20} /> },
    { name: 'Личные контакты',   path: '/personal-contacts',  icon: <BookUser size={20} /> },
    { name: 'Настройки',         path: '/settings',           icon: <Settings size={20} /> },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Activity className="logo-icon" size={32} />
        <h2 className="text-gradient">Profiler</h2>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(item => (
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

      <div className="sidebar-footer" />
    </aside>
  );
};

export default Sidebar;
