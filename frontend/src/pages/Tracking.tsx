import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { 
  RefreshCcw, Search, ExternalLink, Plus, Trash2, Folder, FolderOpen, 
  ChevronDown, ChevronRight, Download, Settings as SettingsIcon, Tag, X 
} from 'lucide-react';
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
  const [importingFolderId, setImportingFolderId] = useState<string | null>(null);
  const [tgFolders, setTgFolders] = useState<any[]>([]);
  const [tgFoldersLoading, setTgFoldersLoading] = useState(false);

  // Folder Editing State
  const [editingFolder, setEditingFolder] = useState<any>(null);
  const [folderFormData, setFolderFormData] = useState({ name: '', description: '', tags_str: '' });

  const handleOpenEditFolder = (folder: any) => {
    setEditingFolder(folder);
    setFolderFormData({
      name: folder.name,
      description: folder.description || '',
      tags_str: (folder.tags || []).join(', ')
    });
  };

  const handleUpdateFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const tags = folderFormData.tags_str.split(',').map(s => s.trim()).filter(s => !!s);
      await api.patch(`/api/tracking/folders/${editingFolder.id}`, {
        name: folderFormData.name,
        description: folderFormData.description,
        tags: tags
      });
      setEditingFolder(null);
      mutateFolders();
      mutate();
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Update failed'));
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

  const handleOpenImport = async (folderId: string) => {
    setImportingFolderId(folderId);
    setTgFoldersLoading(true);
    setTgFolders([]);
    try {
      const res = await api.get('/api/telegram/folders');
      setTgFolders(res.data.folders || []);
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Could not load Telegram folders'));
      setImportingFolderId(null);
    } finally {
      setTgFoldersLoading(false);
    }
  };

  const handleImportFromTg = async (folderId: string, tgFolder: any) => {
    if (!window.confirm(`Import ${tgFolder.channel_count} channels from Telegram folder "${tgFolder.name}"?`)) return;
    try {
      const res = await api.post('/api/telegram/folders/import', {
        folder_id: folderId,
        peer_ids: tgFolder.peer_ids,
      });
      const { added, moved, total } = res.data;
      alert(`Done: ${added} added, ${moved} moved to this folder (${total} total)`);
      setImportingFolderId(null);
      mutate();
      mutateFolders();
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Import failed'));
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
      {/* Data Tab */}
      {(
        <>
          {/* Sync Status */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.1))',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: '12px',
              padding: '20px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <RefreshCcw size={20} style={{ color: '#3b82f6' }} />
                <h3 style={{ color: '#f8fafc', margin: 0, fontSize: '16px' }}>Статус Синхронизации</h3>
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
                      <p style={{ color: '#64748b', margin: 0, fontSize: '11px' }}>Каналы</p>
                      <p style={{ color: '#3b82f6', margin: '4px 0 0', fontSize: '16px', fontWeight: '600' }}>{channelsCount}</p>
                    </div>
                    <div>
                      <p style={{ color: '#64748b', margin: 0, fontSize: '11px' }}>Сообщений</p>
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
                            {isRunning ? '⏳ Загружается...' : hasError ? '❌ Ошибка' : '✓ Готово'}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ color: '#cbd5e1', textAlign: 'center', padding: '16px', fontSize: '13px' }}>
                  Загрузка...
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
              <h1 style={{ color: '#f8fafc', margin: 0, fontSize: '24px', fontWeight: '700' }}>Каналы</h1>
              <p style={{ color: '#64748b', margin: '6px 0 0', fontSize: '14px' }}>Отслеживаемые Telegram каналы и группы</p>
            </div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              {showNewFolderInput ? (
                <form onSubmit={handleCreateFolder} style={{ display: 'flex', gap: '8px' }}>
                  <input
                    autoFocus
                    type="text"
                    placeholder="Имя папки..."
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
                  }}>Создать</button>
                  <button type="button" onClick={() => { setShowNewFolderInput(false); setNewFolderName(''); }} style={{
                    padding: '8px 12px',
                    background: 'rgba(148, 163, 184, 0.1)',
                    border: '1px solid rgba(148, 163, 184, 0.2)',
                    color: '#94a3b8',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '13px'
                  }}>Отмена</button>
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
                  Новая папка
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
                {isSyncing ? 'Синхронизация...' : 'Синхронизировать'}
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
              placeholder="Поиск каналов..."
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
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ color: '#f8fafc', fontWeight: '600', fontSize: '14px' }}>{folder.name}</span>
                    {folder.tags && folder.tags.length > 0 && (
                      <div style={{ display: 'flex', gap: '4px', marginTop: '4px', flexWrap: 'wrap' }}>
                        {folder.tags.map((tag: string) => (
                          <span key={tag} style={{ fontSize: '10px', background: 'rgba(255,255,255,0.05)', color: '#94a3b8', padding: '1px 5px', borderRadius: '3px', border: '1px solid rgba(255,255,255,0.1)' }}>
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <span style={{
                    padding: '1px 8px',
                    background: 'rgba(168, 85, 247, 0.15)',
                    color: '#c084fc',
                    borderRadius: '10px',
                    fontSize: '11px'
                  }}>{channels.length}</span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={e => { e.stopPropagation(); handleOpenEditFolder(folder); }}
                    style={{
                      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      width: '28px', height: '28px',
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '4px', color: '#94a3b8', cursor: 'pointer'
                    }}
                    title="Folder Settings"
                  >
                    <SettingsIcon size={13} />
                  </button>
                  <button
                    onClick={e => { e.stopPropagation(); handleOpenImport(folder.id); }}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: '5px',
                      padding: '4px 10px', height: '28px',
                      background: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                      borderRadius: '4px', color: '#10b981', cursor: 'pointer', fontSize: '12px'
                    }}
                    title="Import channels from Telegram folder"
                  >
                    <Download size={12} /> Import
                  </button>
                  <button
                    onClick={e => { e.stopPropagation(); handleDeleteFolder(folder.id, folder.name); }}
                    style={{
                      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      width: '28px', height: '28px',
                      background: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: '4px', color: '#fca5a5', cursor: 'pointer'
                    }}
                    title="Delete folder"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

              {/* Import modal */}
              {importingFolderId === folder.id && (
                <div style={{
                  padding: '16px',
                  borderBottom: isCollapsed ? 'none' : '1px solid rgba(148, 163, 184, 0.1)',
                  background: 'rgba(16, 185, 129, 0.04)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{ color: '#94a3b8', fontSize: '13px', fontWeight: '600' }}>
                      Select Telegram folder to import:
                    </span>
                    <button onClick={() => setImportingFolderId(null)} style={{
                      background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '18px', lineHeight: 1
                    }}>×</button>
                  </div>
                  {tgFoldersLoading ? (
                    <div style={{ color: '#64748b', fontSize: '13px' }}>Loading Telegram folders...</div>
                  ) : tgFolders.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '13px' }}>No Telegram folders found (or not authorized)</div>
                  ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {tgFolders.map((tf: any) => (
                        <button
                          key={tf.id}
                          onClick={() => handleImportFromTg(folder.id, tf)}
                          style={{
                            padding: '6px 14px',
                            background: 'rgba(16, 185, 129, 0.1)',
                            border: '1px solid rgba(16, 185, 129, 0.3)',
                            borderRadius: '6px',
                            color: '#10b981',
                            cursor: 'pointer',
                            fontSize: '13px',
                            display: 'flex', alignItems: 'center', gap: '6px'
                          }}
                        >
                          <Folder size={13} />
                          {tf.name}
                          <span style={{
                            padding: '0 6px',
                            background: 'rgba(16, 185, 129, 0.2)',
                            borderRadius: '8px',
                            fontSize: '11px'
                          }}>{tf.channel_count}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

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
                Нет каналов или папок
              </div>
            )}
          </div>
        </>
      )}

      {/* Folder Edit Modal */}
      {editingFolder && (
        <div className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100 }}>
          <div className="modal-content serpent-card" style={{ width: '450px', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Настройки папки</h2>
              <button onClick={() => setEditingFolder(null)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}><X size={20} /></button>
            </div>
            <form onSubmit={handleUpdateFolder}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Имя папки</label>
                <input 
                  type="text" 
                  value={folderFormData.name} 
                  onChange={e => setFolderFormData({...folderFormData, name: e.target.value})}
                  style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: 'white' }}
                  required
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Описание</label>
                <textarea 
                  value={folderFormData.description} 
                  onChange={e => setFolderFormData({...folderFormData, description: e.target.value})}
                  style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: 'white', minHeight: '80px' }}
                  placeholder="О чем эта папка..."
                />
              </div>
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Тэги / Ключевые слова (через запятую)</label>
                <div style={{ position: 'relative' }}>
                  <Tag size={14} style={{ position: 'absolute', left: '10px', top: '12px', color: '#64748b' }} />
                  <input 
                    type="text" 
                    value={folderFormData.tags_str} 
                    onChange={e => setFolderFormData({...folderFormData, tags_str: e.target.value})}
                    style={{ width: '100%', padding: '10px 10px 10px 32px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: 'white' }}
                    placeholder="crypto, airdrops, news..."
                  />
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button type="button" onClick={() => setEditingFolder(null)} style={{ padding: '10px 16px', background: 'transparent', border: '1px solid #1e293b', color: '#94a3b8', borderRadius: '8px', cursor: 'pointer' }}>Отмена</button>
                <button type="submit" style={{ padding: '10px 20px', background: '#10b981', border: 'none', color: 'white', borderRadius: '8px', fontWeight: '600', cursor: 'pointer' }}>Сохранить</button>
              </div>
            </form>
          </div>
        </div>
      )}

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
