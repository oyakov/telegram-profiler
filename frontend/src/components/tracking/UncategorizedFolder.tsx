import React from 'react';
import { ChevronDown, ChevronRight, Folder } from 'lucide-react';
import ChannelRow from './ChannelRow';

interface UncategorizedFolderProps {
  channels: any[];
  isCollapsed: boolean;
  onToggle: (id: string) => void;
  onDeleteChannel: (id: string, title: string) => void;
}

const UncategorizedFolder: React.FC<UncategorizedFolderProps> = ({
  channels,
  isCollapsed,
  onToggle,
  onDeleteChannel
}) => {
  if (channels.length === 0) return null;

  return (
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
          borderBottom: isCollapsed ? 'none' : '1px solid rgba(148, 163, 184, 0.1)',
          userSelect: 'none'
        }}
        onClick={() => onToggle('__uncategorized__')}
      >
        {isCollapsed
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
        }}>{channels.length}</span>
      </div>
      {!isCollapsed && (
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
            {channels.map((ch: any) => (
              <ChannelRow key={ch.id} ch={ch} onDelete={onDeleteChannel} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default UncategorizedFolder;
