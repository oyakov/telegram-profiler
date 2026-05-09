import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { Search } from 'lucide-react';
import './Dashboard.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Dashboard: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');

  const { data: stats, error: statsError, isLoading: statsLoading } = useSWR('/api/stats', fetcher);
  const { data: tracking } = useSWR('/api/tracking/channels', fetcher);
  const { data: foldersData } = useSWR('/api/tracking/folders', fetcher);
  const { data: contacts } = useSWR('/api/contacts', fetcher);
  const { data: user } = useSWR('/api/telegram/user', fetcher);

  const folders = foldersData?.folders || [];

  const isLoading = statsLoading || !stats || !tracking;
  if (statsError) {
    const statusCode = statsError.response?.status;
    if (statusCode === 401) {
      return <div className="error">Please log in to view dashboard data</div>;
    }
    return <div className="error">Failed to load dashboard data</div>;
  }
  if (isLoading) return <div className="loading">Loading intelligence...</div>;

  const userName = user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : 'User';
  const userInitial = userName.charAt(0).toUpperCase();

  return (
    <div className="dashboard-page">
      <div className="profile-section serpent-card">
        <div className="profile-avatar">{userInitial}</div>
        <div className="profile-info">
          <h2 className="profile-workspace">{userName}</h2>
          <div className="profile-stats">
            <div className="profile-stat">
              <span className="stat-label">Контактов</span>
              <span className="stat-value">{stats?.total_contacts || 0}</span>
            </div>
            <div className="profile-stat">
              <span className="stat-label">Папок</span>
              <span className="stat-value">{folders?.length || 0}</span>
            </div>
            <div className="profile-stat">
              <span className="stat-label">Каналов</span>
              <span className="stat-value">{tracking?.channels?.length || 0}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="tables-section">
        <div className="table-container">
          <h3>Папки по проектам</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Тип</th>
                <th>Сообщений</th>
              </tr>
            </thead>
            <tbody>
              {folders && folders.length > 0 ? (
                folders.map((folder: any) => (
                  <tr key={folder.id}>
                    <td>{folder.name || folder.title}</td>
                    <td>{folder.folder_type || 'folder'}</td>
                    <td>{folder.message_count || 0}</td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={3} className="empty-state">Нет загруженных папок</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="table-container">
          <h3>Личные контакты</h3>
          <div className="search-box">
            <Search size={16} />
            <input
              type="text"
              placeholder="Поиск контактов..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Имя</th>
                <th>Статус</th>
                <th>Сообщений</th>
              </tr>
            </thead>
            <tbody>
              {contacts && contacts.length > 0 ? (
                contacts
                  .filter((contact: any) =>
                    (contact.name || contact.first_name || '').toLowerCase().includes(searchQuery.toLowerCase())
                  )
                  .map((contact: any) => (
                    <tr key={contact.id}>
                      <td>{contact.name || contact.first_name || 'Unknown'}</td>
                      <td>{contact.status || 'active'}</td>
                      <td>{contact.message_count || 0}</td>
                    </tr>
                  ))
              ) : (
                <tr><td colSpan={3} className="empty-state">Нет контактов</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
