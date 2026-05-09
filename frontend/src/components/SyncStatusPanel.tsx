import React, { useState } from 'react';
import useSWR from 'swr';
import { Play, RotateCw, ChevronDown, ChevronUp, ChevronRight, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../services/api';
import './SyncStatusPanel.css';

interface BatchLog {
  batch_number: number;
  status: 'pending' | 'processing' | 'success' | 'failed';
  messages: number;
  offset: number;
  duration_ms?: number;
  error?: string;
  retry_attempt: number;
}

interface ChannelStatus {
  id: string;
  title: string;
  telegram_id: string;
  phase: 'pending' | 'metadata' | 'syncing' | 'reconciling' | 'complete' | 'error';
  progress_percent: number;
  messages_synced: number;
  estimated_total?: number;
  eta_minutes?: number;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

interface FolderStatus {
  id: string;
  name: string;
  progress_percent: number;
  channel_count: number;
  channels: ChannelStatus[];
}

const fetcher = (url: string) => api.get(url).then(res => res.data);

const ProgressBar: React.FC<{ percent: number; status: string }> = ({ percent, status }) => {
  const getColor = () => {
    if (status === 'complete') return '#10b981';
    if (status === 'error') return '#ef4444';
    if (status === 'syncing' || status === 'processing') return '#3b82f6';
    return '#6b7280';
  };

  return (
    <div className="progress-bar-container">
      <div
        className="progress-bar-fill"
        style={{
          width: `${percent}%`,
          backgroundColor: getColor(),
          transition: 'width 0.3s ease'
        }}
      />
      <span className="progress-percent">{Math.round(percent)}%</span>
    </div>
  );
};

const ChannelRow: React.FC<{ channel: ChannelStatus; onViewLogs: (id: string) => void }> = ({
  channel,
  onViewLogs
}) => {
  const [expanded, setExpanded] = useState(false);

  const getPhaseLabel = () => {
    const labels: Record<string, string> = {
      'pending': 'Ожидание',
      'metadata': 'Сканирование',
      'syncing': 'Синхронизация',
      'reconciling': 'Проверка',
      'complete': 'Завершено',
      'error': 'Ошибка'
    };
    return labels[channel.phase] || channel.phase;
  };

  const getStatusIcon = () => {
    if (channel.phase === 'complete') return <CheckCircle size={16} className="text-green" />;
    if (channel.phase === 'error') return <AlertCircle size={16} className="text-red" />;
    return null;
  };

  return (
    <>
      <div className="channel-row">
        <div className="channel-info">
          <button
            className="expand-btn"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <div className="channel-details">
            <h4>{channel.title}</h4>
            <p className="channel-username">@{channel.telegram_id}</p>
          </div>
        </div>

        <div className="sync-metrics">
          <div className="metric">
            <span className="label">{getPhaseLabel()}</span>
            {getStatusIcon()}
          </div>
          <div className="metric">
            <ProgressBar percent={channel.progress_percent} status={channel.phase} />
          </div>
          <div className="metric">
            <span className="label">
              {channel.messages_synced}
              {channel.estimated_total ? ` / ${channel.estimated_total}` : ''}
            </span>
          </div>
          {channel.eta_minutes && channel.phase !== 'complete' && (
            <div className="metric eta">
              <span className="label">{channel.eta_minutes}м</span>
            </div>
          )}
        </div>

        {expanded && (
          <button
            className="logs-btn"
            onClick={() => onViewLogs(channel.id)}
          >
            Логи
          </button>
        )}
      </div>

      {expanded && channel.error && (
        <div className="error-message">
          <AlertCircle size={14} />
          <span>{channel.error}</span>
        </div>
      )}
    </>
  );
};

const BatchLogModal: React.FC<{
  channelId: string;
  onClose: () => void
}> = ({ channelId, onClose }) => {
  const { data } = useSWR(
    `/api/sync/channel/${channelId}/status`,
    fetcher,
    { refreshInterval: 2000 }
  );

  const batches: BatchLog[] = data?.batches || [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Логи батчей - {data?.title}</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="batch-logs">
          <div className="batch-header">
            <span>Батч</span>
            <span>Статус</span>
            <span>Сообщений</span>
            <span>Время (ms)</span>
            <span>Ошибка</span>
          </div>

          {batches.map(batch => (
            <div key={batch.batch_number} className={`batch-row status-${batch.status}`}>
              <span className="batch-num">#{batch.batch_number}</span>
              <span className="status-badge">
                {batch.status === 'success' && '✓'}
                {batch.status === 'processing' && '⧗'}
                {batch.status === 'pending' && '○'}
                {batch.status === 'failed' && '✗'}
              </span>
              <span>{batch.messages}</span>
              <span>{batch.duration_ms || '—'}</span>
              <span className="error-text">{batch.error || '—'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export const SyncStatusPanel: React.FC = () => {
  const { data, error, isLoading } = useSWR(
    '/api/sync/status',
    fetcher,
    { refreshInterval: 3000 }  // Refresh every 3 seconds
  );

  const [selectedChannelId, setSelectedChannelId] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  const toggleFolder = (folderId: string) => {
    const newSet = new Set(expandedFolders);
    if (newSet.has(folderId)) {
      newSet.delete(folderId);
    } else {
      newSet.add(folderId);
    }
    setExpandedFolders(newSet);
  };

  const handleStartSync = async (folderId: string) => {
    try {
      await api.post(`/api/sync/folder/${folderId}/start`);
    } catch (err) {
      console.error('Failed to start sync:', err);
    }
  };

  if (isLoading) {
    return <div className="sync-panel loading">Загрузка статуса синхронизации...</div>;
  }

  if (error) {
    return <div className="sync-panel error">Ошибка загрузки статуса</div>;
  }

  const folders: FolderStatus[] = data?.folders || [];

  return (
    <div className="sync-status-panel serpent-card">
      <div className="panel-header">
        <h2>📊 Статус Синхронизации</h2>
        <div className="header-controls">
          <span className="auto-refresh">
            <RotateCw size={14} className="spinning" />
            Автообновление: 3s
          </span>
        </div>
      </div>

      {folders.length === 0 ? (
        <div className="empty-state">
          <p>Нет папок для синхронизации</p>
          <small>Синхронизация начнется автоматически после входа в Telegram</small>
        </div>
      ) : (
        <div className="folders-list">
          {folders.map(folder => (
            <div key={folder.id} className="folder-section">
              <div className="folder-header">
                <button
                  className="folder-toggle"
                  onClick={() => toggleFolder(folder.id)}
                >
                  {expandedFolders.has(folder.id) ?
                    <ChevronDown size={18} /> :
                    <ChevronRight size={18} />
                  }
                </button>

                <div className="folder-info">
                  <h3>{folder.name}</h3>
                  <span className="channel-count">{folder.channel_count} каналов</span>
                </div>

                <div className="folder-progress">
                  <ProgressBar percent={folder.progress_percent} status="syncing" />
                </div>

                <button
                  className="start-btn"
                  onClick={() => handleStartSync(folder.id)}
                  title="Начать синхронизацию папки"
                >
                  <Play size={16} />
                </button>
              </div>

              {expandedFolders.has(folder.id) && (
                <div className="channels-list">
                  {folder.channels.map(channel => (
                    <ChannelRow
                      key={channel.id}
                      channel={channel}
                      onViewLogs={setSelectedChannelId}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {selectedChannelId && (
        <BatchLogModal
          channelId={selectedChannelId}
          onClose={() => setSelectedChannelId(null)}
        />
      )}
    </div>
  );
};

export default SyncStatusPanel;
