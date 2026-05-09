import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { Cpu, Clock, Terminal, Play, ListTodo, Zap } from 'lucide-react';
import './AuditLog.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface CeleryTask {
  id: string;
  name: string;
  args?: string;
  kwargs?: string;
  queue?: string;
  worker?: string;
  status: 'running' | 'queued' | 'completed';
  timestamp?: number;
  position?: number;
}

interface CeleryTasksResponse {
  running: CeleryTask[];
  queued: CeleryTask[];
  workers: Record<string, any>;
  summary: {
    total_running: number;
    total_queued: number;
    total_workers: number;
  };
}

const AuditLog: React.FC = () => {
  const { data, error } = useSWR('/api/stats/celery-tasks', fetcher, { refreshInterval: 3000 });
  const { data: metricsData } = useSWR('/api/stats/embeddings-metrics', fetcher, { refreshInterval: 5000 });

  if (error) return <div className="audit-error">Failed to load celery tasks</div>;
  if (!data) return <div className="audit-loading">Loading celery tasks...</div>;

  const celeryData = data as CeleryTasksResponse;
  const allTasks = [...celeryData.running, ...celeryData.queued];

  const getTaskIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Play size={16} className="text-emerald" />;
      case 'queued':
        return <ListTodo size={16} className="text-amber" />;
      default:
        return <Zap size={16} className="text-blue" />;
    }
  };

  const getTaskLabel = (status: string) => {
    switch (status) {
      case 'running':
        return 'Выполняется';
      case 'queued':
        return 'В очереди';
      default:
        return 'Неизвестно';
    }
  };

  const formatTaskName = (name: string) => {
    return name.split('.').pop() || name;
  };

  return (
    <div className="audit-log-container serpent-card">
      <div className="audit-header">
        <Terminal size={18} className="text-accent" />
        <h3>Аудит задач Celery</h3>
      </div>

      {/* Summary stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '12px',
        marginBottom: '24px',
        padding: '16px',
        backgroundColor: 'rgba(255, 255, 255, 0.02)',
        borderRadius: '8px',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#10b981' }}>
            {celeryData.summary.total_running}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#8b949e' }}>Выполняется</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f59e0b' }}>
            {celeryData.summary.total_queued}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#8b949e' }}>В очереди</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#3b82f6' }}>
            {celeryData.summary.total_workers}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#8b949e' }}>Workers</div>
        </div>
      </div>

      {/* Worker stats */}
      {celeryData.summary.total_workers > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem', color: '#8b949e', textTransform: 'uppercase' }}>
            Статус Workers
          </h4>
          <div style={{ display: 'grid', gap: '8px' }}>
            {Object.entries(celeryData.workers).map(([worker, stats]: [string, any]) => (
              <div key={worker} style={{
                padding: '12px',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '6px',
                borderLeft: '3px solid #3b82f6',
              }}>
                <div style={{ fontWeight: 500, color: '#c9d1d9', marginBottom: '4px' }}>{worker}</div>
                <div style={{ fontSize: '0.875rem', color: '#8b949e' }}>
                  Pool: {stats.pool} | Max: {stats.max_concurrency} | Active: {stats.active}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks list */}
      <div>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem', color: '#8b949e', textTransform: 'uppercase' }}>
          Задачи
        </h4>
        <div className="audit-list">
          {allTasks.length > 0 ? (
            allTasks.map((task: CeleryTask, idx: number) => {
              const isEmbeddingsTask = task.name?.includes('embeddings') || task.name?.includes('EMBEDDINGS');
              const taskMetrics = isEmbeddingsTask && metricsData ? metricsData.current_minute : null;

              return (
                <div key={task.id || idx} className={`audit-item ${task.status === 'running' ? 'success' : 'error'}`}
                  style={{ borderLeft: `3px solid ${task.status === 'running' ? '#10b981' : '#f59e0b'}` }}>
                  <div className="audit-icon">
                    {getTaskIcon(task.status)}
                  </div>
                  <div className="audit-content">
                    <div className="audit-main">
                      <span className="audit-type">{formatTaskName(task.name || 'unknown')}</span>
                      <span className="audit-details">
                        {task.status === 'running' ? `Worker: ${task.worker || 'unknown'}` : `Position: ${task.position || 0}`}
                      </span>
                    </div>
                    {/* Embeddings metrics */}
                    {taskMetrics && (
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '12px',
                        margin: '8px 0',
                        padding: '8px',
                        backgroundColor: 'rgba(59, 130, 246, 0.08)',
                        borderRadius: '6px',
                      }}>
                        <div style={{ fontSize: '0.875rem' }}>
                          <div style={{ color: '#3b82f6', fontWeight: 600 }}>{taskMetrics.tokens_processed}</div>
                          <div style={{ color: '#8b949e', fontSize: '0.75rem' }}>tokens/min</div>
                        </div>
                        <div style={{ fontSize: '0.875rem' }}>
                          <div style={{ color: '#3b82f6', fontWeight: 600 }}>{taskMetrics.requests_processed}</div>
                          <div style={{ color: '#8b949e', fontSize: '0.75rem' }}>requests/min</div>
                        </div>
                      </div>
                    )}
                    <div className="audit-meta">
                      <span className="audit-model"><Cpu size={12} /> {getTaskLabel(task.status)}</span>
                      <span className="audit-time"><Clock size={12} /> {task.queue || 'processing'}</span>
                      {task.timestamp && <span style={{ fontSize: '0.65rem', color: '#475569' }}>
                        {new Date(task.timestamp * 1000).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>}
                      <span className="audit-date">{task.id ? task.id.slice(0, 12) : 'n/a'}...</span>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-secondary text-center py-4">Нет активных задач</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuditLog;
