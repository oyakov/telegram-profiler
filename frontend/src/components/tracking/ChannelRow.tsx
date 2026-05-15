import React from 'react';
import { ExternalLink, Trash2 } from 'lucide-react';

interface ChannelRowProps {
  ch: any;
  onDelete: (id: string, title: string) => void;
}

const ChannelRow: React.FC<ChannelRowProps> = ({ ch, onDelete }) => (
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

export default ChannelRow;
