import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { RefreshCw, Activity, Database, Zap, Cpu } from 'lucide-react';
import { DataFlowTree, SystemFlow } from '../components/DataFlowExplorer';
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
      <div className="embeddings-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={20} className="text-venom" />
            Векторное хранилище
          </h3>
          <p className="text-secondary" style={{ margin: '4px 0 0', fontSize: '0.9rem' }}>Состояние эмбеддингов и семантического поиска</p>
        </div>
        <button
          className={`btn-reindex ${reindexStatus}`}
          onClick={handleReindex}
          disabled={reindexing}
        >
          <RefreshCw size={18} className={reindexing ? 'spin' : ''} />
          {reindexing ? 'Переиндексируется...' : 'Переиндексировать'}
        </button>
      </div>

      <div className="embeddings-stats" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
        <div className="stat">
          <span className="label">Всего векторов:</span>
          <span className="value" style={{ fontSize: '1.5rem', fontWeight: '700', color: '#10b981' }}>{stats.total_embeddings.toLocaleString()}</span>
        </div>
        <div className="stat">
          <span className="label">Ожидает обработки:</span>
          <span className="value" style={{ fontSize: '1.5rem', fontWeight: '700', color: stats.messages_needing_embeddings > 0 ? '#f59e0b' : '#10b981' }}>
            {stats.messages_needing_embeddings.toLocaleString()}
          </span>
        </div>
        <div className="stat" style={{ gridColumn: 'span 2' }}>
          <span className="label">Общий прогресс индексации:</span>
          <div className="progress-bar" style={{ marginTop: '10px' }}>
            <div className="progress-fill" style={{ width: `${stats.progress_percent}%` }}></div>
            <span className="progress-text">{stats.progress_percent.toFixed(1)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

const Monitoring: React.FC = () => {
  const { data: treeData } = useSWR('/api/stats/tree', fetcher, { refreshInterval: 5000 });
  const { data: metricsData } = useSWR('/api/stats/prometheus', fetcher, { refreshInterval: 5000 });

  return (
    <div className="monitoring-page animate-fade-in">
      <div className="page-header" style={{ marginBottom: '32px' }}>
        <h1 className="text-gradient" style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Архитектура данных</h1>
        <p className="text-secondary" style={{ fontSize: '1.1rem' }}>Визуализация потоков, иерархии и состояния AI-конвейера</p>
      </div>

      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Zap size={20} className="text-venom" />
          Поток данных (Data Pipeline)
        </h2>
        <SystemFlow metrics={metricsData} />
      </div>

      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Database size={20} className="text-blue" />
          Data Explorer
        </h2>
        {treeData ? (
          <DataFlowTree tree={treeData.tree} />
        ) : (
          <div className="loading serpent-card" style={{ padding: '40px', textAlign: 'center' }}>
            <Activity size={32} className="spin text-blue" style={{ marginBottom: '16px' }} />
            <p>Анализ иерархии баз данных...</p>
          </div>
        )}
      </div>

      <EmbeddingsManager />

      <style>{`
        .loading { display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .spin { animation: spin 2s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Monitoring;
