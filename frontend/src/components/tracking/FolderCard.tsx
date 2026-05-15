import React from 'react';
import { 
  ChevronDown, ChevronRight, Folder, FolderOpen, 
  Settings as SettingsIcon, Download, Trash2 
} from 'lucide-react';
import ChannelRow from './ChannelRow';

interface FolderCardProps {
  folder: any;
  channels: any[];
  isCollapsed: boolean;
  onToggle: (id: string) => void;
  onEdit: (folder: any) => void;
  onImport: (id: string) => void;
  onDelete: (id: string, name: string) => void;
  onDeleteChannel: (id: string, title: string) => void;
  importingFolderId: string | null;
  tgFolders: any[];
  tgFoldersLoading: boolean;
  onCloseImport: () => void;
  onImportFromTg: (folderId: string, tgFolder: any) => void;
}

const FolderCard: React.FC<FolderCardProps> = ({
  folder, channels, isCollapsed, onToggle, onEdit, onImport, onDelete, 
  onDeleteChannel, importingFolderId, tgFolders, tgFoldersLoading, 
  onCloseImport, onImportFromTg
}) => {
  return (
    <div style={{
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
        onClick={() => onToggle(folder.id)}
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
            onClick={e => { e.stopPropagation(); onEdit(folder); }}
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
            onClick={e => { e.stopPropagation(); onImport(folder.id); }}
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
            onClick={e => { e.stopPropagation(); onDelete(folder.id, folder.name); }}
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

      {/* Import section */}
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
            <button onClick={onCloseImport} style={{
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
                  onClick={() => onImportFromTg(folder.id, tf)}
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
              <ChannelRow key={ch.id} ch={ch} onDelete={onDeleteChannel} />
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
};

export default FolderCard;
