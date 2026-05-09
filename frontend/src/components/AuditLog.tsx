import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { Cpu, Clock, Terminal, ListTodo, Zap, Trash2, RefreshCw, Activity } from 'lucide-react';
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
  context?: string;
  progress?: number;
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
  const { data, error, mutate } = useSWR('/api/stats/celery-tasks', fetcher, { refreshInterval: 2000 });
  const { data: metricsData } = useSWR('/api/stats/prometheus', fetcher, { refreshInterval: 5000 });
  const [isPurging, setIsPurging] = useState(false);

  const handlePurge = async () => {
    if (!window.confirm('Вы уверены, что хотите очистить все очереди задач? Это удалит все ожидающие задачи.')) return;
    
    setIsPurging(true);
    try {
      await api.post('/api/stats/celery-tasks/purge');
      await mutate();
    } catch (err) {
      console.error('Failed to purge tasks:', err);
      alert('Ошибка при очистке очередей');
    } finally {
      setIsPurging(false);
    }
  };

  if (error) return <div className="audit-error serpent-card" style={{ padding: '40px', textAlign: 'center' }}>Ошибка загрузки задач</div>;
  if (!data) return <div className="audit-loading" style={{ padding: '40px', textAlign: 'center' }}>Загрузка...</div>;

  const celeryData = data as CeleryTasksResponse;
  const allTasks = [...celeryData.running, ...celeryData.queued];
  const throughput = metricsData?.throughput || { ingestion: 0 };

  const getTaskIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Activity size={16} className="text-blue spin" />;
      case 'queued':
        return <ListTodo size={16} className="text-amber" />;
      default:
        return <Zap size={16} className="text-blue" />;
    }
  };

  const formatTaskName = (name: string) => {
    const parts = name.split('.');
    return parts[parts.length - 1].toUpperCase();
  };

  return (
    <div className="audit-log-container serpent-card">
      <div className="audit-header" style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        padding: '16px 20px',
        borderBottom: '1px solid rgba(16, 185, 129, 0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Terminal size={18} className="text-venom" />
          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Мониторинг очередей Celery</h3>
        </div>

        <button 
          className="btn-venom" 
          onClick={handlePurge}
          disabled={isPurging || celeryData.summary.total_queued === 0}
          style={{ 
            padding: '6px 16px', 
            fontSize: '0.8rem', 
            background: 'rgba(239, 68, 68, 0.1)',
            borderColor: '#ef4444',
            color: '#ef4444',
            opacity: celeryData.summary.total_queued > 0 ? 1 : 0.4,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          {isPurging ? <RefreshCw size={14} className="spin" /> : <Trash2 size={14} />}
          {isPurging ? 'Очистка...' : 'Очистить очереди'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1px', background: 'rgba(16, 185, 129, 0.1)', marginBottom: '24px' }}>
        <div style={{ padding: '20px', textAlign: 'center', background: 'var(--surface-color)' }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#10b981' }}>{celeryData.summary.total_running}</div>
          <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '1px' }}>Активно</div>
        </div>
        <div style={{ padding: '20px', textAlign: 'center', background: 'var(--surface-color)' }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f59e0b' }}>{celeryData.summary.total_queued}</div>
          <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '1px' }}>В очереди</div>
        </div>
        <div style={{ padding: '20px', textAlign: 'center', background: 'var(--surface-color)' }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#3b82f6' }}>{celeryData.summary.total_workers}</div>
          <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '1px' }}>Воркеры</div>
        </div>
      </div>

      <div className="audit-list" style={{ padding: '0 20px 20px' }}>
        {allTasks.length > 0 ? (
          allTasks.map((task: any, idx: number) => (
            <div key={task.id || idx} className={`audit-item ${task.status === 'running' ? 'active' : ''}`} 
                 style={{ 
                   background: task.status === 'running' ? 'rgba(59, 130, 246, 0.05)' : 'rgba(255,255,255,0.02)',
                   borderLeft: `4px solid ${task.status === 'running' ? '#3b82f6' : '#f59e0b'}`,
                   marginBottom: '12px',
                   padding: '16px',
                   borderRadius: '4px',
                   position: 'relative'
                 }}>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {getTaskIcon(task.status)}
                  <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc' }}>
                    {formatTaskName(task.name)}
                  </span>
                  <span style={{ 
                    fontSize: '0.7rem', 
                    background: 'rgba(255,255,255,0.1)', 
                    padding: '2px 6px', 
                    borderRadius: '4px',
                    color: '#94a3b8'
                  }}>
                    {task.queue}
                  </span>
                </div>
                {task.status === 'running' && (
                  <div style={{ fontSize: '0.75rem', color: '#3b82f6', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Activity size={12} /> {throughput.ingestion} msg/min
                  </div>
                )}
              </div>

              <div style={{ color: '#e2e8f0', fontSize: '0.95rem', marginBottom: '12px', fontWeight: 500 }}>
                {task.context || 'Системная задача'}
              </div>

              {task.progress !== null && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '4px', color: '#94a3b8' }}>
                    <span>Общий прогресс канала</span>
                    <span>{task.progress}%</span>
                  </div>
                  <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${task.progress}%`, background: '#3b82f6', transition: 'width 0.3s' }} />
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#64748b' }}>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <span><Cpu size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> {task.worker?.split('@')[1] || 'pending'}</span>
                  <span><Clock size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> {task.timestamp ? new Date(task.timestamp * 1000).toLocaleTimeString() : 'ожидание'}</span>
                </div>
                <div style={{ fontFamily: 'monospace', opacity: 0.5 }}>{task.id?.slice(0, 8)}...</div>
              </div>
            </div>
          ))
        ) : (
          <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>
            <Zap size={32} style={{ marginBottom: '12px', opacity: 0.2 }} />
            <p>Нет активных или ожидающих задач</p>
          </div>
        )}
      </div>

      <style>{`
        .audit-item.active {
          box-shadow: 0 0 15px rgba(59, 130, 246, 0.1);
          animation: pulse-border 2s infinite;
        }
        @keyframes pulse-border {
          0% { border-left-color: #3b82f6; }
          50% { border-left-color: #60a5fa; }
          100% { border-left-color: #3b82f6; }
        }
        .spin { animation: spin 2s linear infinite; }
      `}</style>
    </div>
  );
};

export default AuditLog;
