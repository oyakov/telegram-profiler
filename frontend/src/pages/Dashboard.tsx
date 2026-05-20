import React, { useState, useRef, useEffect } from 'react';
import useSWR from 'swr';
import api, { fetcher } from '../services/api';
import { Search, RefreshCw } from 'lucide-react';
import './Dashboard.css';

interface Folder {
  id: string;
  name?: string;
  title?: string;
  folder_type?: string;
  message_count?: number;
}

interface Contact {
  id: string;
  name?: string;
  first_name?: string;
  status?: string;
  message_count?: number;
}

const Dashboard: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const isMountedRef = useRef(true);

  // Reset to true on every mount (including React StrictMode's double-invocation)
  // so the isMounted check in handleManualSync works correctly after remount.
  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  const { data: stats, error: statsError, isLoading: statsLoading, mutate: mutateStats } = useSWR('/api/stats', fetcher);
  const { data: tracking, mutate: mutateTracking } = useSWR('/api/tracking/channels', fetcher);
  const { data: foldersData, mutate: mutateFolders } = useSWR('/api/tracking/folders', fetcher);
  const { data: contactsData, mutate: mutateContacts } = useSWR('/api/tracking/contacts', fetcher);
  const { data: user } = useSWR('/api/telegram/user', fetcher);

  const handleManualSync = async () => {
    setSyncing(true);
    setSyncStatus('idle');
    try {
      await api.post('/api/sync/manual');

      const contactsSyncResponse = await api.post('/api/telegram/contacts/sync');
      const contactsTaskId = contactsSyncResponse.data.task_id;

      let contactsSyncComplete = false;
      let pollAttempts = 0;

      while (!contactsSyncComplete && pollAttempts < 60) {
        if (!isMountedRef.current) return;
        pollAttempts++;
        const statusResponse = await api.get(`/api/telegram/contacts/sync/status/${contactsTaskId}`);
        const taskStatus = statusResponse.data.status;
        if (taskStatus === 'SUCCESS' || taskStatus === 'FAILURE') {
          contactsSyncComplete = true;
        } else {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }

      if (!isMountedRef.current) return;
      mutateStats();
      mutateTracking();
      mutateFolders();
      mutateContacts();
      setSyncStatus('success');
      setTimeout(() => { if (isMountedRef.current) setSyncStatus('idle'); }, 3000);
    } catch (err) {
      if (!isMountedRef.current) return;
      console.error('Sync failed:', err);
      setSyncStatus('error');
    } finally {
      if (isMountedRef.current) setSyncing(false);
    }
  };

  const folders: Folder[] = foldersData?.folders || [];
  const contacts: Contact[] = contactsData?.contacts || [];

  if (statsError) {
    return (
      <div className="error">
        {statsError.response?.status === 401
          ? 'Необходима авторизация'
          : 'Не удалось загрузить данные'}
      </div>
    );
  }
  if (statsLoading || !stats) return <div className="loading">Загрузка данных...</div>;

  const userName = user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : 'Пользователь';
  const userInitial = userName.charAt(0).toUpperCase();

  return (
    <div className="dashboard-page">
      <div className="profile-section serpent-card no-hover">
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
              <span className="stat-value">{folders.length}</span>
            </div>
            <div className="profile-stat">
              <span className="stat-label">Каналов</span>
              <span className="stat-value">{tracking?.channels?.length || 0}</span>
            </div>
          </div>
        </div>
        <div className="sync-controls">
          <button
            className="sync-btn"
            onClick={handleManualSync}
            disabled={syncing}
            title="Синхронизировать папки и контакты"
            aria-label="Синхронизировать"
          >
            <RefreshCw size={18} className={syncing ? 'spinning' : ''} />
          </button>
          {syncStatus === 'success' && (
            <span style={{ fontSize: '0.85rem', color: '#10b981' }}>✓ Готово</span>
          )}
          {syncStatus === 'error' && (
            <span style={{ fontSize: '0.85rem', color: '#ef4444' }}>✗ Ошибка</span>
          )}
        </div>
      </div>

      <div className="tables-section">
        <div className="table-container">
          <h3>Папки</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Тип</th>
                <th>Сообщений</th>
              </tr>
            </thead>
            <tbody>
              {folders.length > 0 ? (
                folders.map(folder => (
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
              onChange={e => setSearchQuery(e.target.value)}
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
              {contacts.length > 0 ? (
                contacts
                  .filter(c =>
                    (c.name || c.first_name || '').toLowerCase().includes(searchQuery.toLowerCase())
                  )
                  .map(contact => (
                    <tr key={contact.id}>
                      <td>{contact.name || contact.first_name || 'Неизвестно'}</td>
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
