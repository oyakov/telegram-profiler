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
  const { data: stats, error: statsError, mutate: mutateStats } = useSWR<EmbeddingsStats>('/api/stats/embeddings', fetcher);
  const [reindexing, setReindexing] = useState(false);
  const [reindexStatus, setReindexStatus] = useState<'idle' | 'queued' | 'success' | 'error'>('idle');

  const isLoading = !stats && !statsError;

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

  if (statsError) return <div className="error">Failed to load embeddings stats</div>;

  return (
    <div className="embeddings-manager serpent-card no-hover" style={{ position: 'relative', overflow: 'hidden', padding: '24px' }}>
      {isLoading && <div className="card-loading-bar" />}
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
          disabled={reindexing || isLoading}
        >
          <RefreshCw size={18} className={reindexing ? 'spin' : ''} />
          {reindexing ? 'Переиндексируется...' : 'Переиндексировать'}
        </button>
      </div>

      <div className="embeddings-stats" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
        <div className="stat" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span className="label">Всего векторов:</span>
          {isLoading ? (
            <div className="skeleton-placeholder" style={{ width: '100px', height: '1.5rem', marginTop: '4px' }} />
          ) : (
            <span className="value" style={{ fontSize: '1.5rem', fontWeight: '700', color: '#10b981' }}>{(stats?.total_embeddings || 0).toLocaleString()}</span>
          )}
        </div>
        <div className="stat" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span className="label">Ожидает обработки:</span>
          {isLoading ? (
            <div className="skeleton-placeholder" style={{ width: '80px', height: '1.5rem', marginTop: '4px' }} />
          ) : (
            <span className="value" style={{ fontSize: '1.5rem', fontWeight: '700', color: (stats?.messages_needing_embeddings || 0) > 0 ? '#f59e0b' : '#10b981' }}>
              {(stats?.messages_needing_embeddings || 0).toLocaleString()}
            </span>
          )}
        </div>
        <div className="stat" style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span className="label">Общий прогресс индексации:</span>
          {isLoading ? (
            <div className="skeleton-placeholder" style={{ width: '100%', height: '24px', borderRadius: '12px', marginTop: '10px' }} />
          ) : (
            <div className="progress-bar" style={{ marginTop: '10px' }}>
              <div className="progress-fill" style={{ width: `${stats?.progress_percent || 0}%` }}></div>
              <span className="progress-text">{(stats?.progress_percent || 0).toFixed(1)}%</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const Monitoring: React.FC = () => {
  const { data: treeData, mutate: mutateTrees } = useSWR('/api/stats/tree', fetcher, { refreshInterval: 20000 });
  const { data: metricsData } = useSWR('/api/stats/prometheus', fetcher, { refreshInterval: 30000 });
  const { data: embedProvider } = useSWR('/api/stats/embedding-provider', fetcher, { refreshInterval: 60000 });

  const handleStartSync = async (folderId: string) => {
    try {
      await api.post(`/api/sync/folder/${folderId}/start`);
      setTimeout(() => mutateTrees(), 1000);
    } catch (err) {
      console.error('Failed to start sync:', err);
    }
  };

  return (
    <div className="monitoring-page animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="text-gradient">Архитектура данных</h1>
          <p className="text-secondary">Визуализация потоков, иерархии и состояния AI-конвейера</p>
        </div>
      </div>

      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Zap size={20} className="text-venom" />
          Data Pipeline
        </h2>
        <SystemFlow metrics={metricsData} embedProvider={embedProvider} />
      </div>


      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Database size={20} className="text-blue" />
          Data Explorer
        </h2>
        {treeData ? (
          <div className="serpent-card no-hover" style={{ padding: '24px' }}>
            <DataFlowTree tree={treeData.tree} onSync={handleStartSync} />
          </div>
        ) : (
          <div className="serpent-card no-hover" style={{ position: 'relative', overflow: 'hidden', padding: '40px', minHeight: '300px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
            <div className="card-loading-bar" />
            <Activity size={32} className="spin text-blue" style={{ animation: 'spin 2s linear infinite' }} />
            <p className="text-secondary" style={{ margin: 0 }}>Анализ иерархии баз данных...</p>
          </div>
        )}
      </div>

      <EmbeddingsManager />

      <style>{`
        .spin { animation: spin 2s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Monitoring;
