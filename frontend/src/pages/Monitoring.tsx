import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import {
  Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { Shield, Coins, Zap, Clock } from 'lucide-react';
import './Monitoring.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Monitoring: React.FC = () => {
  const { data: stats, error } = useSWR('/api/stats/ai-monitoring', fetcher);

  if (error) return <div className="error">Failed to load monitoring data</div>;
  if (!stats) return <div className="loading">Gathering AI metrics...</div>;

  const tokenData = [
    { name: 'Prompt', value: stats.total_prompt_tokens || 0 },
    { name: 'Completion', value: stats.total_completion_tokens || 0 },
  ];

  const COLORS = ['#10b981', '#f59e0b'];

  return (
    <div className="monitoring-page">
      <div className="page-header">
        <h1 className="text-gradient">AI Мониторинг</h1>
        <p className="text-secondary">Производительность LLM и эффективность экстракции</p>
      </div>

      <div className="metrics-grid">
        <div className="monitor-card serpent-card">
          <Zap className="icon purple" size={32} />
          <div className="info">
            <span className="label">Успешность</span>
            <span className="value">{stats.success_rate?.toFixed(1) || 0}%</span>
          </div>
        </div>
        <div className="monitor-card serpent-card">
          <Coins className="icon yellow" size={32} />
          <div className="info">
            <span className="label">Затраты (est)</span>
            <span className="value">${stats.estimated_cost_usd?.toFixed(4) || 0}</span>
          </div>
        </div>
        <div className="monitor-card serpent-card">
          <Clock className="icon blue" size={32} />
          <div className="info">
            <span className="label">Avg Latency</span>
            <span className="value">{stats.avg_processing_time_ms || 0}ms</span>
          </div>
        </div>
        <div className="monitor-card serpent-card">
          <Shield className="icon green" size={32} />
          <div className="info">
            <span className="label">Всего запусков</span>
            <span className="value">{stats.total_runs || 0}</span>
          </div>
        </div>
      </div>

      <div className="monitoring-charts">
        <div className="chart-container glass">
          <h3>📊 Распределение токенов</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={tokenData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {tokenData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            <div className="legend-item">
              <span className="dot blue"></span> Prompt: {stats.total_prompt_tokens?.toLocaleString()}
            </div>
            <div className="legend-item">
              <span className="dot red"></span> Completion: {stats.total_completion_tokens?.toLocaleString()}
            </div>
          </div>
        </div>

        <div className="chart-container glass">
          <h3>🕒 Статус системы</h3>
          <div className="status-placeholder">
            <div className="status-row">
              <span>Database Connection</span>
              <span className="status-tag ok">OK</span>
            </div>
            <div className="status-row">
              <span>Vector Engine</span>
              <span className="status-tag ok">OK</span>
            </div>
            <div className="status-row">
              <span>Extraction Pipeline</span>
              <span className="status-tag ok">Running</span>
            </div>
            <div className="status-row">
              <span>Embedding Service</span>
              <span className="status-tag warning">Queued (12)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Monitoring;
