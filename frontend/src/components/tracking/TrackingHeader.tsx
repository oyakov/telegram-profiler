import React from 'react';
import { Plus, RefreshCcw } from 'lucide-react';

interface TrackingHeaderProps {
  isSyncing: boolean;
  onSync: () => void;
  showNewFolderInput: boolean;
  setShowNewFolderInput: (show: boolean) => void;
  newFolderName: string;
  setNewFolderName: (name: string) => void;
  onCreateFolder: (e: React.FormEvent) => void;
}

const TrackingHeader: React.FC<TrackingHeaderProps> = ({
  isSyncing,
  onSync,
  showNewFolderInput,
  setShowNewFolderInput,
  newFolderName,
  setNewFolderName,
  onCreateFolder
}) => {
  return (
    <div className="page-header">
      <div>
        <h1 className="text-gradient">Каналы</h1>
        <p className="text-secondary">Отслеживаемые Telegram каналы и группы</p>
      </div>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        {showNewFolderInput ? (
          <form onSubmit={onCreateFolder} style={{ display: 'flex', gap: '8px' }}>
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
          onClick={onSync}
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
  );
};

export default TrackingHeader;
