import { useState, useEffect } from 'react';
import useSWR from 'swr';
import api from '../services/api';

const fetcher = (url: string) => api.get(url).then(res => res.data);

export const useTracking = () => {
  const { data, mutate } = useSWR('/api/tracking/channels', fetcher);
  const { data: foldersData, mutate: mutateFolders } = useSWR('/api/tracking/folders', fetcher);
  const { data: syncData, mutate: mutateSyncStatus } = useSWR('/api/connectors/sync/status', fetcher, { refreshInterval: 2000 });
  
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

  // Initialize all folders as collapsed
  useEffect(() => {
    if (foldersData?.folders && foldersData.folders.length > 0) {
      const allFolderIds = new Set<string>(foldersData.folders.map((f: any) => f.id));
      setCollapsedFolders(allFolderIds);
    }
  }, [foldersData]);

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

  return {
    data,
    foldersData,
    syncData,
    searchTerm,
    setSearchTerm,
    isSyncing,
    collapsedFolders,
    newFolderName,
    setNewFolderName,
    showNewFolderInput,
    setShowNewFolderInput,
    importingFolderId,
    setImportingFolderId,
    tgFolders,
    tgFoldersLoading,
    editingFolder,
    setEditingFolder,
    folderFormData,
    setFolderFormData,
    handleOpenEditFolder,
    handleUpdateFolder,
    handleSync,
    handleCreateFolder,
    handleDeleteFolder,
    handleDeleteChannel,
    handleOpenImport,
    handleImportFromTg,
    toggleFolder
  };
};
