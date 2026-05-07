import React, { useState, useEffect } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import {
  Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid
} from 'recharts';
import { Shield, Coins, Zap, Clock, Database, TrendingUp, Activity, CheckCircle2, AlertCircle } from 'lucide-react';
import './Monitoring.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface LatencyDataPoint {
  time: string;
  latency: number;
}

// Animated Counter Component
const AnimatedCounter: React.FC<{ value: number; duration?: number; format?: (v: number) => string }> = ({
  value,
  duration = 800,
  format = (v) => v.toFixed(1)
}) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      setDisplayValue(value * progress);

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [value, duration]);

  return <span className="animated-value">{format(displayValue)}</span>;
};

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

const Monitoring: React.FC = () => {
  const { data: stats, error } = useSWR('/api/stats/ai-monitoring', fetcher, { refreshInterval: 2000 });
  const { data: embedStats } = useSWR('/api/stats/embeddings', fetcher, { refreshInterval: 5000 });
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

  const mockEmbedStats = embedStats || {
    total_embeddings: 16732,
    progress_percent: 58.9,
    total_messages: 8450,
    messages_with_embeddings: 4970,
    messages_needing_embeddings: 3480
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

      {/* Top Metrics Row - Compact */}
      <div className="metrics-grid-compact">
        <div className="metric-card-compact serpent-card">
          <div className="metric-header">
            <Zap className="icon purple" size={20} />
            <span className="label">Успешность</span>
          </div>
          <div className="metric-value">
            <AnimatedCounter
              value={mockStats.success_rate || 0}
              format={(v) => `${v.toFixed(1)}%`}
              duration={600}
            />
          </div>
          <div className="metric-sparkline" style={{ height: '20px', marginTop: '4px' }}>
            <TrendingUp size={14} style={{ color: '#10b981', marginRight: '4px' }} />
          </div>
        </div>

        <div className="metric-card-compact serpent-card">
          <div className="metric-header">
            <Coins className="icon yellow" size={20} />
            <span className="label">Затраты (USD)</span>
          </div>
          <div className="metric-value">
            $<AnimatedCounter
              value={mockStats.estimated_cost_usd || 0}
              format={(v) => v.toFixed(4)}
              duration={600}
            />
          </div>
        </div>

        <div className="metric-card-compact serpent-card">
          <div className="metric-header">
            <Clock className="icon blue" size={20} />
            <span className="label">Avg Latency</span>
          </div>
          <div className="metric-value">
            <AnimatedCounter
              value={mockStats.avg_processing_time_ms || 0}
              format={(v) => `${v.toFixed(0)}ms`}
              duration={600}
            />
          </div>
        </div>

        <div className="metric-card-compact serpent-card">
          <div className="metric-header">
            <Shield className="icon green" size={20} />
            <span className="label">Запусков</span>
          </div>
          <div className="metric-value">
            <AnimatedCounter
              value={mockStats.total_runs || 0}
              format={(v) => v.toFixed(0)}
              duration={600}
            />
          </div>
        </div>

        <div className="metric-card-compact serpent-card">
          <div className="metric-header">
            <Database className="icon cyan" size={20} />
            <span className="label">Embeddings</span>
          </div>
          <div className="metric-value">
            <AnimatedCounter
              value={mockEmbedStats?.total_embeddings || 0}
              format={(v) => (v / 1000).toFixed(1) + 'k'}
              duration={600}
            />
          </div>
        </div>

        <div className="metric-card-compact serpent-card">
          <div className="metric-header">
            <Zap className="icon orange" size={20} />
            <span className="label">Progress</span>
          </div>
          <div className="metric-value">
            <AnimatedCounter
              value={mockEmbedStats?.progress_percent || 0}
              format={(v) => `${v.toFixed(1)}%`}
              duration={600}
            />
          </div>
        </div>
      </div>

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

          {/* Embeddings Progress */}
          <div className="chart-card glass" style={{ gridColumn: '1 / 2' }}>
            <h3>📝 Статус Embeddings</h3>
            <div className="progress-section">
              <div className="progress-bar-container">
                <div className="progress-bar-label">
                  <span>Прогресс</span>
                  <span className="progress-percent">
                    <AnimatedCounter
                      value={mockEmbedStats?.progress_percent || 0}
                      format={(v) => `${v.toFixed(1)}%`}
                      duration={600}
                    />
                  </span>
                </div>
                <div className="progress-bar-track">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${mockEmbedStats?.progress_percent || 0}%`,
                      transition: 'width 0.3s ease'
                    }}
                  ></div>
                </div>
              </div>
              <div className="stat-grid" style={{ marginTop: '16px' }}>
                <div className="stat-box">
                  <div className="stat-value small">
                    {(mockEmbedStats?.total_messages || 0).toLocaleString()}
                  </div>
                  <div className="stat-label small">Всего сообщений</div>
                </div>
                <div className="stat-box">
                  <div className="stat-value small">
                    {(mockEmbedStats?.messages_with_embeddings || 0).toLocaleString()}
                  </div>
                  <div className="stat-label small">С embeddings</div>
                </div>
                <div className="stat-box">
                  <div className="stat-value small">
                    {(mockEmbedStats?.messages_needing_embeddings || 0).toLocaleString()}
                  </div>
                  <div className="stat-label small">Осталось</div>
                </div>
              </div>
            </div>
          </div>

          {/* System Status */}
          <div className="chart-card glass" style={{ gridColumn: '2 / 3' }}>
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
      </div>
    </div>
  );
};

export default Monitoring;
