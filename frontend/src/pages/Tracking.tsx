import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { RefreshCcw, Search, ExternalLink, Plus, Phone, Trash2, Folder, FolderOpen, ChevronDown, ChevronRight } from 'lucide-react';
import './Tracking.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const ChannelRow: React.FC<{ ch: any; onDelete: (id: string, title: string) => void }> = ({ ch, onDelete }) => (
  <tr style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.08)' }}>
    <td style={{ padding: '11px 16px', color: '#f8fafc' }}>
      <div style={{ fontWeight: '600' }}>{ch.title}</div>
      <div style={{ color: '#64748b', fontSize: '12px', marginTop: '2px' }}>@{ch.username || 'private'}</div>
    </td>
    <td style={{ padding: '11px 16px' }}>
      <span style={{
        display: 'inline-block',
        padding: '2px 8px',
        background: ch.type === 'channel' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(148, 163, 184, 0.1)',
        color: ch.type === 'channel' ? '#3b82f6' : '#94a3b8',
        borderRadius: '4px',
        fontSize: '11px',
        textTransform: 'capitalize'
      }}>{ch.type}</span>
    </td>
    <td style={{ padding: '11px 16px', color: '#10b981', textAlign: 'right', fontWeight: '600' }}>
      {(ch.messages_count || 0).toLocaleString()}
    </td>
    <td style={{ padding: '11px 16px', color: '#64748b', fontSize: '12px' }}>
      {ch.last_sync ? new Date(ch.last_sync).toLocaleDateString() : '—'}
    </td>
    <td style={{ padding: '11px 16px', textAlign: 'center' }}>
      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
        {ch.username && (
          <a
            href={`https://t.me/${ch.username}`}
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              width: '30px', height: '30px',
              background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: '4px', color: '#3b82f6', textDecoration: 'none'
            }}
          >
            <ExternalLink size={13} />
          </a>
        )}
        <button
          onClick={() => onDelete(ch.id, ch.title)}
          style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: '30px', height: '30px',
            background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '4px', color: '#fca5a5', cursor: 'pointer'
          }}
          title="Remove from tracking"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </td>
  </tr>
);

const Tracking: React.FC = () => {
  const { data, mutate } = useSWR('/api/tracking/channels', fetcher);
  const { data: foldersData, mutate: mutateFolders } = useSWR('/api/tracking/folders', fetcher);
  const { data: syncData, mutate: mutateSyncStatus } = useSWR('/api/connectors/status', fetcher, { refreshInterval: 2000 });
  const [searchTerm, setSearchTerm] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(new Set());
  const [newFolderName, setNewFolderName] = useState('');
  const [showNewFolderInput, setShowNewFolderInput] = useState(false);
  const [telegramPhone, setTelegramPhone] = useState('');
  const [telegramCode, setTelegramCode] = useState('');
  const [telegramPassword, setTelegramPassword] = useState('');
  const [telegramStep, setTelegramStep] = useState<'phone' | 'code' | 'password'>('phone');
  const [telegramPhoneHash, setTelegramPhoneHash] = useState('');
  const [telegramLoading, setTelegramLoading] = useState(false);
  const [telegramAuthorized, setTelegramAuthorized] = useState<boolean | null>(null);

  const checkTelegramAuth = async () => {
    try {
      const res = await api.get('/api/telegram/auth/status');
      setTelegramAuthorized(res.data.authorized);
    } catch (err) {
      setTelegramAuthorized(false);
    }
  };

  React.useEffect(() => {
    checkTelegramAuth();
  }, []);

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      const res = await api.post('/api/telegram/auth/send_code', { phone: telegramPhone });
      setTelegramPhoneHash(res.data.phone_code_hash);
      setTelegramStep('code');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Failed to send code'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      const res = await api.post('/api/telegram/auth/verify', {
        phone: telegramPhone,
        code: telegramCode,
        phone_code_hash: telegramPhoneHash,
      });
      if (res.data.status === 'requires_2fa') {
        setTelegramStep('password');
      } else {
        setTelegramAuthorized(true);
        setTelegramPhone('');
        setTelegramCode('');
      }
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Verification failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      await api.post('/api/telegram/auth/2fa', { password: telegramPassword });
      setTelegramAuthorized(true);
      setTelegramPhone('');
      setTelegramCode('');
      setTelegramPassword('');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || '2FA failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect Telegram? You can login again anytime.')) return;
    setTelegramLoading(true);
    try {
      await api.post('/api/telegram/auth/logout');
      setTelegramAuthorized(false);
      setTelegramStep('phone');
      setTelegramPhone('');
      setTelegramCode('');
      setTelegramPassword('');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Logout failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await api.post('/api/connectors/telegram/sync');
      alert('Синхронизация запущена в фоновом режиме');
      mutate();
      mutateSyncStatus();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCreateFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    try {
      await api.post('/api/tracking/folders', { name: newFolderName.trim() });
      setNewFolderName('');
      setShowNewFolderInput(false);
      mutateFolders();
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Failed to create folder'));
    }
  };

  const handleDeleteFolder = async (folderId: string, folderName: string) => {
    const channelsInFolder = data?.channels?.filter((ch: any) => ch.folder_id === folderId) || [];
    const msg = channelsInFolder.length > 0
      ? `Delete folder "${folderName}" and all ${channelsInFolder.length} channels in it?`
      : `Delete folder "${folderName}"?`;
    if (!window.confirm(msg)) return;
    try {
      await api.delete(`/api/tracking/folders/${folderId}`);
      mutate();
      mutateFolders();
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Failed to delete folder'));
    }
  };

  const handleDeleteChannel = async (channelId: string, channelTitle: string) => {
    if (!window.confirm(`Remove channel "${channelTitle}" from tracking?`)) return;
    try {
      await api.delete(`/api/tracking/channels/${channelId}`);
      mutate();
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Failed to delete channel'));
    }
  };

  const toggleFolder = (folderId: string) => {
    setCollapsedFolders(prev => {
      const next = new Set(prev);
      if (next.has(folderId)) next.delete(folderId); else next.add(folderId);
      return next;
    });
  };

  const filteredChannels = data?.channels?.filter((ch: any) =>
    ch.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ch.username?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  // Group channels by folder
  const folders = foldersData?.folders || [];
  const channelsByFolder: Record<string, any[]> = {};
  const uncategorized: any[] = [];
  for (const ch of filteredChannels) {
    if (ch.folder_id) {
      if (!channelsByFolder[ch.folder_id]) channelsByFolder[ch.folder_id] = [];
      channelsByFolder[ch.folder_id].push(ch);
    } else {
      uncategorized.push(ch);
    }
  }

  const channelsCount = data?.channels?.length || 0;
  const totalMessages = data?.channels?.reduce((sum: number, ch: any) => sum + (ch.messages_count || 0), 0) || 0;

  return (
    <div className="tracking-page">
      {/* Top Section: Auth + Sync Status */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
        {/* Telegram Auth Card */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 78, 59, 0.1))',
          border: '1px solid rgba(16, 185, 129, 0.2)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Phone size={20} style={{ color: '#10b981' }} />
            <h3 style={{ color: '#f8fafc', margin: 0, fontSize: '16px' }}>Telegram Auth</h3>
          </div>

          {telegramAuthorized === true ? (
            <div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '12px',
                padding: '12px',
                background: 'rgba(16, 185, 129, 0.1)',
                borderRadius: '8px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>✅</span>
                  <div>
                    <p style={{ color: '#10b981', margin: '0', fontWeight: 'bold', fontSize: '14px' }}>Connected</p>
                    <p style={{ color: '#64748b', margin: '2px 0 0', fontSize: '11px' }}>Session active</p>
                  </div>
                </div>
                <button
                  onClick={handleDisconnect}
                  disabled={telegramLoading}
                  style={{
                    padding: '6px 12px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    color: '#fca5a5',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '4px',
                    cursor: telegramLoading ? 'not-allowed' : 'pointer',
                    fontSize: '12px',
                    fontWeight: 'bold'
                  }}
                >
                  {telegramLoading ? 'Processing...' : 'Disconnect'}
                </button>
              </div>
            </div>
          ) : telegramAuthorized === null ? (
            <div style={{ color: '#cbd5e1', textAlign: 'center', padding: '16px', fontSize: '14px' }}>
              Checking...
            </div>
          ) : (
            <form onSubmit={
              telegramStep === 'phone' ? handleSendCode :
              telegramStep === 'code' ? handleVerifyCode :
              handleVerify2FA
            } style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                {telegramStep === 'phone' && (
                  <>
                    <label style={{ color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>Phone</label>
                    <input
                      type="tel"
                      placeholder="+38123456789"
                      value={telegramPhone}
                      onChange={(e) => setTelegramPhone(e.target.value)}
                      disabled={telegramLoading}
                      autoFocus
                      style={{
                        width: '100%',
                        padding: '8px 10px',
                        marginTop: '6px',
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                        color: '#f8fafc',
                        borderRadius: '6px',
                        fontSize: '13px',
                        boxSizing: 'border-box'
                      }}
                    />
                  </>
                )}
                {telegramStep === 'code' && (
                  <>
                    <label style={{ color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>Code</label>
                    <input
                      type="text"
                      placeholder="123456"
                      value={telegramCode}
                      onChange={(e) => setTelegramCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      disabled={telegramLoading}
                      autoFocus
                      maxLength={6}
                      style={{
                        width: '100%',
                        padding: '8px 10px',
                        marginTop: '6px',
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                        color: '#f8fafc',
                        borderRadius: '6px',
                        fontSize: '13px',
                        boxSizing: 'border-box',
                        letterSpacing: '4px'
                      }}
                    />
                  </>
                )}
                {telegramStep === 'password' && (
                  <>
                    <label style={{ color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>2FA Password</label>
                    <input
                      type="password"
                      placeholder="Your password"
                      value={telegramPassword}
                      onChange={(e) => setTelegramPassword(e.target.value)}
                      disabled={telegramLoading}
                      autoFocus
                      style={{
                        width: '100%',
                        padding: '8px 10px',
                        marginTop: '6px',
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                        color: '#f8fafc',
                        borderRadius: '6px',
                        fontSize: '13px',
                        boxSizing: 'border-box'
                      }}
                    />
                  </>
                )}
              </div>
              <button
                type="submit"
                disabled={telegramLoading}
                style={{
                  padding: '10px 16px',
                  background: telegramLoading ? 'rgba(16, 185, 129, 0.5)' : 'linear-gradient(135deg, #10b981, #059669)',
                  color: '#f8fafc',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: '600',
                  cursor: telegramLoading ? 'not-allowed' : 'pointer',
                  fontSize: '13px'
                }}
              >
                {telegramLoading ? '⏳ Processing...' : `Continue →`}
              </button>
            </form>
          )}
        </div>

        {/* Sync Status Card */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.1))',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <RefreshCcw size={20} style={{ color: '#3b82f6' }} />
            <h3 style={{ color: '#f8fafc', margin: 0, fontSize: '16px' }}>Sync Status</h3>
          </div>

          {syncData?.connectors ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Overall Statistics */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '10px',
                padding: '12px',
                background: 'rgba(148, 163, 184, 0.05)',
                borderRadius: '8px'
              }}>
                <div>
                  <p style={{ color: '#64748b', margin: 0, fontSize: '11px' }}>Channels</p>
                  <p style={{ color: '#3b82f6', margin: '4px 0 0', fontSize: '16px', fontWeight: '600' }}>{channelsCount}</p>
                </div>
                <div>
                  <p style={{ color: '#64748b', margin: 0, fontSize: '11px' }}>Messages</p>
                  <p style={{ color: '#10b981', margin: '4px 0 0', fontSize: '16px', fontWeight: '600' }}>{totalMessages.toLocaleString()}</p>
                </div>
              </div>

              {/* Connector Status */}
              {syncData.connectors.map((connector: any) => {
                const isRunning = connector.status === 'running';
                const hasError = connector.status === 'error';

                return (
                  <div key={connector.connector} style={{
                    padding: '12px',
                    background: isRunning ? 'rgba(59, 130, 246, 0.1)' : hasError ? 'rgba(239, 68, 68, 0.1)' : 'rgba(148, 163, 184, 0.05)',
                    border: `1px solid ${isRunning ? 'rgba(59, 130, 246, 0.3)' : hasError ? 'rgba(239, 68, 68, 0.3)' : 'rgba(148, 163, 184, 0.15)'}`,
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <p style={{ color: '#f8fafc', margin: '0', fontWeight: '600', textTransform: 'capitalize', fontSize: '14px' }}>{connector.connector}</p>
                      <p style={{ color: '#64748b', margin: '2px 0 0', fontSize: '11px' }}>
                        {isRunning ? '⏳ Downloading...' : hasError ? '❌ Error' : '✓ Ready'}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ color: '#cbd5e1', textAlign: 'center', padding: '16px', fontSize: '13px' }}>
              Loading...
            </div>
          )}
        </div>
      </div>

      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px'
      }}>
        <div>
          <h1 style={{ color: '#f8fafc', margin: 0, fontSize: '24px', fontWeight: '700' }}>Channels</h1>
          <p style={{ color: '#64748b', margin: '6px 0 0', fontSize: '14px' }}>Tracked Telegram channels and groups</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {showNewFolderInput ? (
            <form onSubmit={handleCreateFolder} style={{ display: 'flex', gap: '8px' }}>
              <input
                autoFocus
                type="text"
                placeholder="Folder name..."
                value={newFolderName}
                onChange={e => setNewFolderName(e.target.value)}
                style={{
                  padding: '8px 12px',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(168, 85, 247, 0.4)',
                  color: '#f8fafc',
                  borderRadius: '6px',
                  fontSize: '13px',
                  outline: 'none',
                  width: '180px'
                }}
              />
              <button type="submit" style={{
                padding: '8px 14px',
                background: 'linear-gradient(135deg, #a855f7, #7c3aed)',
                border: 'none',
                color: '#fff',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: '600'
              }}>Create</button>
              <button type="button" onClick={() => { setShowNewFolderInput(false); setNewFolderName(''); }} style={{
                padding: '8px 12px',
                background: 'rgba(148, 163, 184, 0.1)',
                border: '1px solid rgba(148, 163, 184, 0.2)',
                color: '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '13px'
              }}>Cancel</button>
            </form>
          ) : (
            <button
              onClick={() => setShowNewFolderInput(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 16px',
                background: 'rgba(168, 85, 247, 0.1)',
                border: '1px solid rgba(168, 85, 247, 0.3)',
                color: '#a855f7',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: '600'
              }}
            >
              <Plus size={16} />
              New Folder
            </button>
          )}
          <button
            onClick={handleSync}
            disabled={isSyncing}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 16px',
              background: isSyncing ? 'rgba(16, 185, 129, 0.5)' : 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#10b981',
              borderRadius: '6px',
              cursor: isSyncing ? 'not-allowed' : 'pointer',
              fontSize: '13px',
              fontWeight: '600'
            }}
          >
            <RefreshCcw size={16} style={{ animation: isSyncing ? 'spin 1s linear infinite' : 'none' }} />
            {isSyncing ? 'Syncing...' : 'Sync Now'}
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 16px',
        background: 'rgba(30, 41, 59, 0.5)',
        border: '1px solid rgba(148, 163, 184, 0.15)',
        borderRadius: '8px',
        marginBottom: '20px'
      }}>
        <Search size={18} style={{ color: '#64748b' }} />
        <input
          type="text"
          placeholder="Search channels..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: '#f8fafc',
            outline: 'none',
            fontSize: '14px'
          }}
        />
      </div>

      {/* Folders + Channels */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {folders.map((folder: any) => {
          const channels = channelsByFolder[folder.id] || [];
          const isCollapsed = collapsedFolders.has(folder.id);
          return (
            <div key={folder.id} style={{
              background: 'rgba(30, 41, 59, 0.3)',
              border: '1px solid rgba(148, 163, 184, 0.15)',
              borderRadius: '8px',
              overflow: 'hidden'
            }}>
              {/* Folder Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  cursor: 'pointer',
                  borderBottom: isCollapsed ? 'none' : '1px solid rgba(148, 163, 184, 0.1)',
                  background: 'rgba(168, 85, 247, 0.05)',
                  userSelect: 'none'
                }}
                onClick={() => toggleFolder(folder.id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {isCollapsed
                    ? <ChevronRight size={16} style={{ color: '#94a3b8' }} />
                    : <ChevronDown size={16} style={{ color: '#94a3b8' }} />}
                  {isCollapsed
                    ? <Folder size={16} style={{ color: '#a855f7' }} />
                    : <FolderOpen size={16} style={{ color: '#a855f7' }} />}
                  <span style={{ color: '#f8fafc', fontWeight: '600', fontSize: '14px' }}>{folder.name}</span>
                  <span style={{
                    padding: '1px 8px',
                    background: 'rgba(168, 85, 247, 0.15)',
                    color: '#c084fc',
                    borderRadius: '10px',
                    fontSize: '11px'
                  }}>{channels.length}</span>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); handleDeleteFolder(folder.id, folder.name); }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '28px',
                    height: '28px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '4px',
                    color: '#fca5a5',
                    cursor: 'pointer'
                  }}
                  title="Delete folder"
                >
                  <Trash2 size={13} />
                </button>
              </div>

              {/* Channels Table */}
              {!isCollapsed && (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  {channels.length > 0 && (
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}>
                        <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '500' }}>Channel</th>
                        <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '500' }}>Type</th>
                        <th style={{ padding: '10px 16px', textAlign: 'right', color: '#64748b', fontWeight: '500' }}>Messages</th>
                        <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '500' }}>Last Sync</th>
                        <th style={{ padding: '10px 16px', textAlign: 'center', color: '#64748b', fontWeight: '500' }}>Actions</th>
                      </tr>
                    </thead>
                  )}
                  <tbody>
                    {channels.map((ch: any) => (
                      <ChannelRow key={ch.id} ch={ch} onDelete={handleDeleteChannel} />
                    ))}
                    {channels.length === 0 && (
                      <tr>
                        <td colSpan={5} style={{ padding: '20px 16px', textAlign: 'center', color: '#475569', fontSize: '13px' }}>
                          No channels in this folder
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          );
        })}

        {/* Uncategorized */}
        {uncategorized.length > 0 && (
          <div style={{
            background: 'rgba(30, 41, 59, 0.3)',
            border: '1px solid rgba(148, 163, 184, 0.15)',
            borderRadius: '8px',
            overflow: 'hidden'
          }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px 16px',
                cursor: 'pointer',
                borderBottom: collapsedFolders.has('__uncategorized__') ? 'none' : '1px solid rgba(148, 163, 184, 0.1)',
                userSelect: 'none'
              }}
              onClick={() => toggleFolder('__uncategorized__')}
            >
              {collapsedFolders.has('__uncategorized__')
                ? <ChevronRight size={16} style={{ color: '#94a3b8' }} />
                : <ChevronDown size={16} style={{ color: '#94a3b8' }} />}
              <Folder size={16} style={{ color: '#64748b' }} />
              <span style={{ color: '#94a3b8', fontWeight: '600', fontSize: '14px' }}>Uncategorized</span>
              <span style={{
                padding: '1px 8px',
                background: 'rgba(148, 163, 184, 0.1)',
                color: '#64748b',
                borderRadius: '10px',
                fontSize: '11px'
              }}>{uncategorized.length}</span>
            </div>
            {!collapsedFolders.has('__uncategorized__') && (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}>
                    <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '500' }}>Channel</th>
                    <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '500' }}>Type</th>
                    <th style={{ padding: '10px 16px', textAlign: 'right', color: '#64748b', fontWeight: '500' }}>Messages</th>
                    <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '500' }}>Last Sync</th>
                    <th style={{ padding: '10px 16px', textAlign: 'center', color: '#64748b', fontWeight: '500' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {uncategorized.map((ch: any) => (
                    <ChannelRow key={ch.id} ch={ch} onDelete={handleDeleteChannel} />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {filteredChannels.length === 0 && folders.length === 0 && (
          <div style={{
            padding: '48px',
            textAlign: 'center',
            color: '#64748b',
            background: 'rgba(30, 41, 59, 0.3)',
            border: '1px solid rgba(148, 163, 184, 0.15)',
            borderRadius: '8px'
          }}>
            No channels or folders yet
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default Tracking;
