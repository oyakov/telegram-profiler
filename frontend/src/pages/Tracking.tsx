import React from 'react';
import { useTracking } from '../hooks/useTracking';
import './Tracking.css';

// Extracted Components
import SyncStatusCard from '../components/tracking/SyncStatusCard';
import FolderCard from '../components/tracking/FolderCard';
import FolderEditModal from '../components/tracking/FolderEditModal';
import TrackingHeader from '../components/tracking/TrackingHeader';
import SearchBar from '../components/tracking/SearchBar';
import UncategorizedFolder from '../components/tracking/UncategorizedFolder';

const Tracking: React.FC = () => {
  const {
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
  } = useTracking();

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
      <SyncStatusCard 
        syncData={syncData} 
        channelsCount={channelsCount} 
        totalMessages={totalMessages} 
      />

      <TrackingHeader 
        isSyncing={isSyncing}
        onSync={handleSync}
        showNewFolderInput={showNewFolderInput}
        setShowNewFolderInput={setShowNewFolderInput}
        newFolderName={newFolderName}
        setNewFolderName={setNewFolderName}
        onCreateFolder={handleCreateFolder}
      />

      <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {folders.map((folder: any) => (
          <FolderCard 
            key={folder.id}
            folder={folder}
            channels={channelsByFolder[folder.id] || []}
            isCollapsed={collapsedFolders.has(folder.id)}
            onToggle={toggleFolder}
            onEdit={handleOpenEditFolder}
            onImport={handleOpenImport}
            onDelete={handleDeleteFolder}
            onDeleteChannel={handleDeleteChannel}
            importingFolderId={importingFolderId}
            tgFolders={tgFolders}
            tgFoldersLoading={tgFoldersLoading}
            onCloseImport={() => setImportingFolderId(null)}
            onImportFromTg={handleImportFromTg}
          />
        ))}

        <UncategorizedFolder 
          channels={uncategorized}
          isCollapsed={collapsedFolders.has('__uncategorized__')}
          onToggle={toggleFolder}
          onDeleteChannel={handleDeleteChannel}
        />

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

      {editingFolder && (
        <FolderEditModal 
          folder={editingFolder}
          formData={folderFormData}
          setFormData={setFolderFormData}
          onClose={() => setEditingFolder(null)}
          onSubmit={handleUpdateFolder}
        />
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
