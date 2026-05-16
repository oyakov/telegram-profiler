import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { Activity, Zap, Database, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import './TaskMonitoring.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const TaskMonitoring: React.FC = () => {
  const { data: embeddingStats, error: embeddingError } = useSWR('/api/stats/embeddings', fetcher, { refreshInterval: 15000 });
  const { data: workerStats, error: workerError } = useSWR('/api/stats/workers', fetcher, { refreshInterval: 15000 });
  const [isReindexing, setIsReindexing] = useState(false);

  const handleReindex = async () => {
    try {
      setIsReindexing(true);
      await api.post('/api/stats/embeddings/reindex');
      // Refresh stats after triggering reindex
      setTimeout(() => setIsReindexing(false), 1000);
    } catch (error) {
      console.error('Reindex failed:', error);
      setIsReindexing(false);
    }
  };

  if (embeddingError || workerError) {
    return <div className="task-monitoring-error">Failed to load monitoring data</div>;
  }

  if (!embeddingStats || !workerStats) {
    return <div className="task-monitoring-loading">Loading task monitoring...</div>;
  }

  const progressValue = Math.min(100, embeddingStats.progress_percent);
  const chartData = [
    {
      name: 'Embedding Stats',
      embedded: embeddingStats.messages_with_embeddings,
      pending: embeddingStats.messages_needing_embeddings
    }
  ];

  return (
    <div className="task-monitoring-container">
      <div className="monitoring-section">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <Zap size={24} className="text-emerald" />
          <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Закачка эмбеддингов</h3>
        </div>

        <div className="monitoring-stats-grid">
          <div className="stat-box serpent-card">
            <div className="stat-label">
              <Database size={18} className="text-blue" />
              Всего сообщений
            </div>
            <div className="stat-value">{embeddingStats.total_messages}</div>
          </div>

          <div className="stat-box serpent-card">
            <div className="stat-label">
              <CheckCircle2 size={18} className="text-emerald" />
              С эмбеддингами
            </div>
            <div className="stat-value">{embeddingStats.messages_with_embeddings}</div>
          </div>

          <div className="stat-box serpent-card">
            <div className="stat-label">
              <AlertCircle size={18} className="text-yellow" />
              Ожидают закачки
            </div>
            <div className="stat-value">{embeddingStats.messages_needing_embeddings}</div>
          </div>

          <div className="stat-box serpent-card">
            <div className="stat-label">
              <Activity size={18} className="text-purple" />
              Всего эмбеддингов
            </div>
            <div className="stat-value">{embeddingStats.total_embeddings}</div>
          </div>
        </div>

        <div className="progress-section serpent-card">
          <div className="progress-header">
            <span>Прогресс закачки</span>
            <span className="progress-percent">{progressValue.toFixed(1)}%</span>
          </div>
          <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: `${progressValue}%` }}></div>
          </div>
          <button
            className="reindex-button"
            onClick={handleReindex}
            disabled={isReindexing}
          >
            {isReindexing ? 'Переиндексирование...' : 'Начать переиндексирование'}
          </button>
        </div>

        <div className="chart-section serpent-card">
          <h4>Статистика эмбеддингов</h4>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid #10b981' }} />
              <Legend />
              <Bar dataKey="embedded" stackId="a" fill="#10b981" name="С эмбеддингами" />
              <Bar dataKey="pending" stackId="a" fill="#f59e0b" name="Ожидают" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="monitoring-section">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <Activity size={24} className="text-emerald" />
          <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Рабочие процессы</h3>
        </div>

        {workerStats.workers && workerStats.workers.length > 0 ? (
          <div className="workers-list">
            {workerStats.workers.map((worker: any, idx: number) => (
              <div key={idx} className="worker-card serpent-card">
                <div className="worker-header">
                  <div className="worker-name">
                    <Activity size={16} className={`text-${worker.status === 'online' ? 'emerald' : 'red'}`} />
                    {worker.name}
                  </div>
                  <div className={`worker-status ${worker.status}`}>
                    {worker.status === 'online' ? '🟢 Online' : '🔴 Offline'}
                  </div>
                </div>
                <div className="worker-details">
                  <div className="detail-item">
                    <span className="detail-label">Активные задачи:</span>
                    <span className="detail-value">{worker.active_tasks}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Макс параллелизм:</span>
                    <span className="detail-value">{worker.max_concurrency}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Зарегистрировано задач:</span>
                    <span className="detail-value">{worker.registered_tasks_count}</span>
                  </div>
                </div>
                {worker.tasks && worker.tasks.length > 0 && (
                  <div className="current-tasks">
                    <div className="tasks-label">Текущие задачи:</div>
                    {worker.tasks.slice(0, 3).map((task: any, tidx: number) => (
                      <div key={tidx} className="task-item">
                        <Clock size={12} />
                        <span>{task.name || 'Task'}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="no-workers">Нет активных рабочих процессов</div>
        )}
      </div>
    </div>
  );
};

export default TaskMonitoring;
