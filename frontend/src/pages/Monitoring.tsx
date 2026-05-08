import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { RefreshCw } from 'lucide-react';
import './Monitoring.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface EmbeddingsStats {
  total_messages: number;
  messages_with_embeddings: number;
  messages_needing_embeddings: number;
  total_embeddings: number;
  progress_percent: number;
}

// Embeddings Manager Component
function EmbeddingsManager() {
  const { data: stats, mutate: mutateStats } = useSWR<EmbeddingsStats>('/api/stats/embeddings', fetcher);
  const [reindexing, setReindexing] = useState(false);
  const [reindexStatus, setReindexStatus] = useState<'idle' | 'queued' | 'success' | 'error'>('idle');

  const handleReindex = async () => {
    setReindexing(true);
    setReindexStatus('queued');
    try {
      await api.post('/api/stats/embeddings/reindex');
      setReindexStatus('success');
      await mutateStats();
      setTimeout(() => setReindexStatus('idle'), 3000);
    } catch (err) {
      setReindexStatus('error');
      console.error('Reindex failed:', err);
      setTimeout(() => setReindexStatus('idle'), 3000);
    } finally {
      setReindexing(false);
    }
  };

  if (!stats) return <div className="loading">Загрузка...</div>;

  return (
    <div className="embeddings-manager serpent-card">
      <div className="embeddings-header">
        <div>
          <h3>🤖 Управление данными</h3>
          <p className="text-secondary">Переиндексируйте векторы для улучшения качества поиска</p>
        </div>
        <button
          className={`btn-reindex ${reindexStatus}`}
          onClick={handleReindex}
          disabled={reindexing}
          title="Перегенерировать все векторы для лучшего поиска"
        >
          <RefreshCw size={18} />
          {reindexing ? 'Переиндексируется...' : 'Переиндексировать'}
        </button>
      </div>

      <div className="embeddings-stats">
        <div className="stat">
          <span className="label">Сообщений:</span>
          <span className="value">{stats.total_messages}</span>
        </div>
        <div className="stat">
          <span className="label">С векторами:</span>
          <span className="value">{stats.messages_with_embeddings}</span>
        </div>
        <div className="stat">
          <span className="label">Нужны векторы:</span>
          <span className="value">{stats.messages_needing_embeddings}</span>
        </div>
        <div className="stat">
          <span className="label">Прогресс:</span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${stats.progress_percent}%` }}></div>
            <span className="progress-text">{stats.progress_percent.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {reindexStatus === 'success' && <div className="status-msg success">✓ Переиндексировка запущена!</div>}
      {reindexStatus === 'error' && <div className="status-msg error">✗ Ошибка при переиндексировке</div>}
    </div>
  );
}

const Monitoring: React.FC = () => {
  return (
    <div className="monitoring-page">
      <div className="page-header">
        <h1 className="text-gradient">⚡ Данные</h1>
        <p className="text-secondary">Производительность конвейера и эффективность AI-экстракции</p>
      </div>

      <EmbeddingsManager />
    </div>
  );
};

export default Monitoring;
