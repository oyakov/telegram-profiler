import React, { useState, useRef, useEffect } from 'react';
import useSWR from 'swr';
import api, { fetcher } from '../services/api';
import { Search, RefreshCw, ChevronUp, ChevronDown } from 'lucide-react';
import './Dashboard.css';

interface Folder {
  id: string;
  name?: string;
  folder_type?: string;
  message_count?: number;
  recent_count?: number;
}

interface Contact {
  id: string;
  name?: string;
  username?: string;
  message_count?: number;
}

type SortDir = 'asc' | 'desc';

function useSortable<T>(items: T[], defaultKey: keyof T) {
  const [sortKey, setSortKey] = useState<keyof T>(defaultKey);
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const toggle = (key: keyof T) => {
    if (key === sortKey) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const sorted = [...items].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const Indicator = ({ col }: { col: keyof T }) =>
    sortKey !== col ? null : sortDir === 'asc'
      ? <ChevronUp size={13} className="sort-icon active" />
      : <ChevronDown size={13} className="sort-icon active" />;

  return { sorted, toggle, sortKey, sortDir, Indicator };
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

  const { data: stats, error: statsError, mutate: mutateStats } = useSWR('/api/stats', fetcher);
  const { data: tracking, error: trackingError, mutate: mutateTracking } = useSWR('/api/tracking/channels', fetcher);
  const { data: foldersData, error: foldersError, mutate: mutateFolders } = useSWR('/api/tracking/folders', fetcher);
  const { data: contactsData, error: contactsError, mutate: mutateContacts } = useSWR('/api/tracking/contacts', fetcher);
  const { data: authStatus, error: authStatusError } = useSWR('/api/telegram/auth/status', fetcher);
  const user = authStatus?.profile;

  const isStatsLoading = !stats && !statsError;
  const isTrackingLoading = !tracking && !trackingError;
  const isFoldersLoading = !foldersData && !foldersError;
  const isContactsLoading = !contactsData && !contactsError;
  const isAuthStatusLoading = !authStatus && !authStatusError;
  const isProfileLoading = isAuthStatusLoading || isStatsLoading;

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

  const folderSort = useSortable(folders, 'message_count' as keyof Folder);
  const contactSort = useSortable(
    contacts.filter(c => (c.name || '').toLowerCase().includes(searchQuery.toLowerCase())),
    'message_count' as keyof Contact
  );

  if (statsError) {
    return (
      <div className="error">
        {statsError.response?.status === 401
          ? 'Необходима авторизация'
          : 'Не удалось загрузить данные'}
      </div>
    );
  }

  const userName = user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : (isProfileLoading ? '' : 'Пользователь');
  const userInitial = userName ? userName.charAt(0).toUpperCase() : '?';
  const selectedDb = localStorage.getItem('selected_db') || 'crm';
  const avatarUrl = user?.telegram_id
    ? `/api/telegram/media/avatar/${user.telegram_id}?db=${selectedDb}`
    : null;

  return (
    <div className="dashboard-page">
      <div className="profile-section serpent-card no-hover">
        {isProfileLoading && <div className="card-loading-bar" />}
        <div className="profile-avatar">
          {avatarUrl
            ? <img src={avatarUrl} alt={userName} className="profile-avatar-img" onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none'; (e.currentTarget.parentElement!.querySelector('.profile-avatar-initial') as HTMLElement).style.display = 'flex'; }} />
            : null}
          <span className="profile-avatar-initial" style={avatarUrl ? { display: 'none' } : {}}>{userInitial}</span>
        </div>
        <div className="profile-info">
          {isProfileLoading ? (
            <div className="skeleton-placeholder name-skeleton" />
          ) : (
            <h2 className="profile-workspace">{userName}</h2>
          )}
          
          {isProfileLoading ? (
            <div className="skeleton-placeholder username-skeleton" />
          ) : (
            user?.username && <div className="profile-telegram-username">@{user.username}</div>
          )}

          {isProfileLoading ? (
            <div className="skeleton-placeholder bio-skeleton" />
          ) : (
            user?.bio && <div className="profile-bio">{user.bio}</div>
          )}

          <div className="profile-stats">
            <div className="profile-stat">
              <span className="stat-label">Контактов</span>
              {isStatsLoading ? (
                <div className="skeleton-placeholder count-skeleton" />
              ) : (
                <span className="stat-value">{stats?.total_contacts || 0}</span>
              )}
            </div>
            <div className="profile-stat">
              <span className="stat-label">Папок</span>
              {isFoldersLoading ? (
                <div className="skeleton-placeholder count-skeleton" />
              ) : (
                <span className="stat-value">{folders.length}</span>
              )}
            </div>
            <div className="profile-stat">
              <span className="stat-label">Каналов</span>
              {isTrackingLoading ? (
                <div className="skeleton-placeholder count-skeleton" />
              ) : (
                <span className="stat-value">{tracking?.channels?.length || 0}</span>
              )}
            </div>
          </div>
        </div>
        <div className="sync-controls">
          <button
            className={`sync-btn-labeled ${syncStatus === 'success' ? 'sync-success' : syncStatus === 'error' ? 'sync-error' : ''}`}
            onClick={handleManualSync}
            disabled={syncing}
          >
            <RefreshCw size={15} className={syncing ? 'spinning' : ''} />
            {syncing
              ? 'Синхронизирую...'
              : syncStatus === 'success'
              ? '✓ Синхронизировано'
              : syncStatus === 'error'
              ? '✗ Ошибка'
              : 'Синхронизировать'}
          </button>
        </div>
      </div>

      <div className="tables-section">
        <div className="table-container">
          {isFoldersLoading && <div className="card-loading-bar" />}
          <h3>Папки</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th className="sortable" onClick={() => folderSort.toggle('name')}>
                  Название <folderSort.Indicator col="name" />
                </th>
                <th className="sortable" onClick={() => folderSort.toggle('message_count')}>
                  Сообщений <folderSort.Indicator col="message_count" />
                </th>
              </tr>
            </thead>
            <tbody>
              {isFoldersLoading ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <tr key={`folder-skeleton-${idx}`}>
                    <td>
                      <div className="skeleton-placeholder text-skeleton" style={{ width: '120px' }} />
                    </td>
                    <td>
                      <div className="skeleton-placeholder text-skeleton" style={{ width: '60px' }} />
                    </td>
                  </tr>
                ))
              ) : folderSort.sorted.length > 0 ? (
                folderSort.sorted.map(folder => (
                  <tr key={folder.id}>
                    <td>{folder.name}</td>
                    <td>
                      {(folder.message_count || 0).toLocaleString()}
                      {(folder.recent_count || 0) > 0 && (
                        <span className="recent-delta"> (+{folder.recent_count!.toLocaleString()})</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={2} className="empty-state">Нет загруженных папок</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="table-container">
          {isContactsLoading && <div className="card-loading-bar" />}
          <h3>Личные контакты</h3>
          <div className="search-box">
            <Search size={16} />
            <input
              type="text"
              placeholder="Поиск контактов..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              disabled={isContactsLoading}
            />
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th className="sortable" onClick={() => contactSort.toggle('name')}>
                  Имя <contactSort.Indicator col="name" />
                </th>
                <th className="sortable" onClick={() => contactSort.toggle('message_count')}>
                  Сообщений <contactSort.Indicator col="message_count" />
                </th>
              </tr>
            </thead>
            <tbody>
              {isContactsLoading ? (
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={`contact-skeleton-${idx}`}>
                    <td>
                      <div className="skeleton-placeholder text-skeleton" style={{ width: '140px' }} />
                    </td>
                    <td>
                      <div className="skeleton-placeholder text-skeleton" style={{ width: '50px' }} />
                    </td>
                  </tr>
                ))
              ) : contactSort.sorted.length > 0 ? (
                contactSort.sorted.map(contact => (
                  <tr key={contact.id}>
                    <td>{contact.name || 'Неизвестно'}</td>
                    <td>{(contact.message_count || 0).toLocaleString()}</td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={2} className="empty-state">Нет контактов</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
