import { useState, useEffect, type FormEvent } from 'react';
import useSWR from 'swr';
import api, { fetcher } from '../services/api';
import { useToast } from '../context/ToastContext';
import { useConfirm } from '../context/ConfirmContext';

interface Folder {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
}

interface Channel {
  id: string;
  folder_id?: string;
  title?: string;
  username?: string;
  messages_count?: number;
}

export const useTracking = () => {
  const { showToast } = useToast();
  const { confirm } = useConfirm();

  const { data, error, mutate } = useSWR('/api/tracking/channels', fetcher);
  const { data: foldersData, error: foldersError, mutate: mutateFolders } = useSWR('/api/tracking/folders', fetcher);
  const { data: syncData, mutate: mutateSyncStatus } = useSWR(
    '/api/connectors/pipeline/sync/status', fetcher, { refreshInterval: 8000 }
  );

  const isLoading = !data && !error;
  const foldersLoading = !foldersData && !foldersError;

  const [searchTerm, setSearchTerm] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(new Set());
  const [foldersInitialized, setFoldersInitialized] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [showNewFolderInput, setShowNewFolderInput] = useState(false);
  const [importingFolderId, setImportingFolderId] = useState<string | null>(null);
  const [tgFolders, setTgFolders] = useState<any[]>([]);
  const [tgFoldersLoading, setTgFoldersLoading] = useState(false);

  const [editingFolder, setEditingFolder] = useState<Folder | null>(null);
  const [folderFormData, setFolderFormData] = useState({ name: '', description: '', tags_str: '' });

  // Collapse all folders on first load only — don't reset when SWR revalidates
  useEffect(() => {
    if (!foldersInitialized && foldersData?.folders?.length > 0) {
      setCollapsedFolders(new Set<string>(foldersData.folders.map((f: Folder) => f.id)));
      setFoldersInitialized(true);
    }
  }, [foldersData, foldersInitialized]);

  const handleOpenEditFolder = (folder: Folder) => {
    setEditingFolder(folder);
    setFolderFormData({
      name: folder.name,
      description: folder.description || '',
      tags_str: (folder.tags || []).join(', '),
    });
  };

  const handleUpdateFolder = async (e: FormEvent) => {
    e.preventDefault();
    if (!editingFolder) return;
    try {
      const tags = folderFormData.tags_str.split(',').map(s => s.trim()).filter(Boolean);
      await api.patch(`/api/tracking/folders/${editingFolder.id}`, {
        name: folderFormData.name,
        description: folderFormData.description,
        tags,
      });
      setEditingFolder(null);
      mutateFolders();
      mutate();
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось обновить папку');
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await api.post('/api/connectors/telegram/sync');
      showToast('info', 'Синхронизация запущена в фоновом режиме');
      mutate();
      mutateSyncStatus();
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось запустить синхронизацию');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCreateFolder = async (e: FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    try {
      await api.post('/api/tracking/folders', { name: newFolderName.trim() });
      setNewFolderName('');
      setShowNewFolderInput(false);
      mutateFolders();
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось создать папку');
    }
  };

  const handleDeleteFolder = async (folderId: string, folderName: string) => {
    const channelsInFolder = (data?.channels as Channel[] || []).filter(ch => ch.folder_id === folderId);
    const msg = channelsInFolder.length > 0
      ? `Удалить папку «${folderName}» и все ${channelsInFolder.length} каналов внутри?`
      : `Удалить папку «${folderName}»?`;
    if (!await confirm(msg, 'Удаление папки')) return;
    try {
      await api.delete(`/api/tracking/folders/${folderId}`);
      mutate();
      mutateFolders();
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось удалить папку');
    }
  };

  const handleDeleteChannel = async (channelId: string, channelTitle: string) => {
    if (!await confirm(`Убрать канал «${channelTitle}» из отслеживания?`, 'Удаление канала')) return;
    try {
      await api.delete(`/api/tracking/channels/${channelId}`);
      mutate();
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось удалить канал');
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
      showToast('error', err.response?.data?.detail || 'Не удалось загрузить папки Telegram');
      setImportingFolderId(null);
    } finally {
      setTgFoldersLoading(false);
    }
  };

  const handleImportFromTg = async (folderId: string, tgFolder: any) => {
    if (!await confirm(
      `Импортировать ${tgFolder.channel_count} каналов из папки Telegram «${tgFolder.name}»?`,
      'Импорт каналов'
    )) return;
    try {
      const res = await api.post('/api/telegram/folders/import', {
        folder_id: folderId,
        peer_ids: tgFolder.peer_ids,
      });
      const { added, moved, total } = res.data;
      showToast('success', `Готово: добавлено ${added}, перемещено ${moved} (всего ${total})`);
      setImportingFolderId(null);
      mutate();
      mutateFolders();
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось импортировать каналы');
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
    toggleFolder,
    isLoading,
    foldersLoading,
  };
};
