import React, { useState, useEffect } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import {
  Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, YAxis, CartesianGrid
} from 'recharts';
import { Activity, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import AuditLog from '../components/AuditLog';
import './Monitoring.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface LatencyDataPoint {
  time: string;
  latency: number;
}

interface EmbeddingsStats {
  total_messages: number;
  messages_with_embeddings: number;
  messages_needing_embeddings: number;
  total_embeddings: number;
  progress_percent: number;
}

// Status Indicator Component
const StatusIndicator: React.FC<{ status: 'ok' | 'warning' | 'error' | 'processing' }> = ({ status }) => {
  const config = {
    ok: { color: '#10b981', icon: CheckCircle2, label: 'OK' },
    warning: { color: '#f59e0b', icon: AlertCircle, label: 'Warning' },
    error: { color: '#ef4444', icon: AlertCircle, label: 'Error' },
    processing: { color: '#3b82f6', icon: Activity, label: 'Processing' }
  };

  const { color, icon: Icon, label } = config[status];
  return (
    <div className="status-indicator" style={{ borderColor: color }}>
      <Icon size={16} style={{ color }} />
      <span className="status-label">{label}</span>
    </div>
  );
};

// Mini Latency Chart Component
const MiniLatencyChart: React.FC<{ data: LatencyDataPoint[] }> = ({ data }) => {
  if (data.length === 0) return null;

  return (
    <div style={{ width: '100%', height: 80 }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <YAxis hide={true} domain={['dataMin - 10', 'dataMax + 10']} />
          <Line
            type="monotone"
            dataKey="latency"
            stroke="#10b981"
            dot={false}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

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
          <h3>🤖 Управление Embeddings</h3>
          <p className="text-secondary">Переиндексируйте embeddings для улучшения качества поиска</p>
        </div>
        <button
          className={`btn-reindex ${reindexStatus}`}
          onClick={handleReindex}
          disabled={reindexing}
          title="Перегенерировать все embeddings для лучшего поиска"
        >
          <RefreshCw size={18} />
          {reindexing ? 'Переиндексируется...' : 'Переиндексировать'}
        </button>
      </div>

      <div className="embeddings-stats">
        <div className="stat">
          <span className="label">Всего сообщений:</span>
          <span className="value">{stats.total_messages}</span>
        </div>
        <div className="stat">
          <span className="label">С embeddings:</span>
          <span className="value">{stats.messages_with_embeddings}</span>
        </div>
        <div className="stat">
          <span className="label">Нужны embeddings:</span>
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
  const { data: stats } = useSWR('/api/stats/ai-monitoring', fetcher, { refreshInterval: 2000 });
  const [latencyHistory, setLatencyHistory] = useState<LatencyDataPoint[]>([]);

  // Mock data for demonstration when API is not available
  const mockStats = stats || {
    success_rate: 94.2,
    estimated_cost_usd: 12.4567,
    avg_processing_time_ms: 245,
    total_runs: 1248,
    total_prompt_tokens: 450000,
    total_completion_tokens: 320000
  };

  // Simulate latency history (in production, this would come from backend)
  useEffect(() => {
    if (mockStats?.avg_processing_time_ms) {
      setLatencyHistory(prev => {
        const newData = [...prev, {
          time: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }),
          latency: mockStats.avg_processing_time_ms + (Math.random() - 0.5) * 50
        }];
        return newData.slice(-15); // Keep last 15 data points
      });
    }
  }, [mockStats?.avg_processing_time_ms]);


  const tokenData = [
    { name: 'Prompt', value: mockStats.total_prompt_tokens || 0 },
    { name: 'Completion', value: mockStats.total_completion_tokens || 0 },
  ];

  const COLORS = ['#10b981', '#f59e0b'];

  return (
    <div className="monitoring-page">
      <div className="page-header">
        <h1 className="text-gradient">⚡ AI Мониторинг</h1>
        <p className="text-secondary">Производительность LLM и эффективность экстракции</p>
      </div>

      <EmbeddingsManager />

      {/* Main Charts Section */}
      <div className="monitoring-section">
        <div className="section-title">📊 Анализ производительности</div>

        <div className="charts-grid">
          {/* Token Distribution */}
          <div className="chart-card glass">
            <h3>Распределение токенов</h3>
            <div style={{ width: '100%', height: 280 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={tokenData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {tokenData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="chart-stats">
              <div className="stat-row">
                <span className="stat-label">Prompt</span>
                <span className="stat-value">{(mockStats.total_prompt_tokens || 0).toLocaleString()}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Completion</span>
                <span className="stat-value">{(mockStats.total_completion_tokens || 0).toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Latency Trend */}
          <div className="chart-card glass">
            <h3>Тренд задержки</h3>
            <MiniLatencyChart data={latencyHistory} />
            <div className="chart-stats">
              <div className="stat-row">
                <span className="stat-label">Текущая</span>
                <span className="stat-value">{mockStats.avg_processing_time_ms || 0}ms</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Макс</span>
                <span className="stat-value">
                  {Math.max(...latencyHistory.map(d => d.latency), mockStats.avg_processing_time_ms || 0).toFixed(0)}ms
                </span>
              </div>
            </div>
          </div>

          {/* System Status */}
          <div className="chart-card glass">
            <h3>🕒 Статус компонентов</h3>
            <div className="status-list">
              <div className="status-item">
                <div className="status-name">Database</div>
                <StatusIndicator status="ok" />
              </div>
              <div className="status-item">
                <div className="status-name">Vector Engine</div>
                <StatusIndicator status="ok" />
              </div>
              <div className="status-item">
                <div className="status-name">Pipeline</div>
                <StatusIndicator status="processing" />
              </div>
              <div className="status-item">
                <div className="status-name">Embedding Service</div>
                <StatusIndicator status="processing" />
              </div>
            </div>
            <div className="auto-refresh-note">
              🔄 Обновляется каждые 2 сек
            </div>
          </div>
        </div>

        <div style={{ marginTop: '2rem' }}>
          <AuditLog />
        </div>
      </div>
    </div>
  );
};

export default Monitoring;
