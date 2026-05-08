import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { Users, MessageSquare, Radio, Mic, Activity, CheckCircle2, AlertCircle } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area 
} from 'recharts';
import './Dashboard.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

// Status Indicator Component (Moved from Monitoring)
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

const MetricCard: React.FC<{ title: string, value: string | number, icon: React.ReactNode, trend?: string }> = ({ title, value, icon, trend }) => (
  <div className="metric-card serpent-card">
    <div className="metric-icon">{icon}</div>
    <div className="metric-info">
      <h3 className="text-secondary">{title}</h3>
      <div className="metric-value">{value}</div>
      {trend && <span className="metric-trend">{trend}</span>}
    </div>
  </div>
);

const Dashboard: React.FC = () => {
  const { data: stats, error: statsError } = useSWR('/api/stats', fetcher);
  const { data: tracking, error: trackingError } = useSWR('/api/tracking/channels', fetcher);
  const { data: timelineData } = useSWR('/api/stats/timeline', fetcher);

  const isLoading = !stats || !tracking;

  if (statsError || trackingError) return <div className="error">Failed to load dashboard data</div>;
  if (isLoading) return <div className="loading">Loading intelligence...</div>;

  const chartData = stats.contacts_by_source ? 
    Object.entries(stats.contacts_by_source).map(([name, value]) => ({ name, value })) : [];

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1 className="text-gradient">Обзор</h1>
        <p className="text-secondary">Сводная аналитика по всем источникам данных</p>
      </div>

      <div className="metrics-grid">
        <MetricCard 
          title="Контактов" 
          value={stats.total_contacts || 0} 
          icon={<Users size={24} />} 
          trend="+12% за неделю" 
        />
        <MetricCard 
          title="Сообщений" 
          value={stats.total_messages || 0} 
          icon={<MessageSquare size={24} />} 
        />
        <MetricCard 
          title="Каналов" 
          value={tracking.channels?.length || 0} 
          icon={<Radio size={24} />} 
        />
        <MetricCard 
          title="Голосовых" 
          value={stats.total_voice_notes || 0} 
          icon={<Mic size={24} />} 
        />
      </div>

      <div className="charts-grid">
        <div className="chart-container timeline-chart full-width serpent-card">
          <h3>📈 Динамика активности</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <AreaChart data={timelineData?.timeline}>
                <defs>
                  <linearGradient id="colorMsg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                <XAxis 
                  dataKey="day" 
                  stroke="#94a3b8" 
                  tickFormatter={(val) => val.split('-').slice(1).join('/')} 
                  fontSize={12}
                />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="messages" 
                  name="Сообщения"
                  stroke="#10b981" 
                  fillOpacity={1} 
                  fill="url(#colorMsg)" 
                />
                <Area 
                  type="monotone" 
                  dataKey="leads" 
                  name="Лиды"
                  stroke="#f59e0b" 
                  fillOpacity={1} 
                  fill="url(#colorLeads)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* System Status Widget */}
        <div className="chart-container serpent-card">
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
            🔄 Обновляется автоматически
          </div>
        </div>

        <div className="chart-container serpent-card">
          <h3>📊 Активность по источникам</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                  itemStyle={{ color: '#3b82f6' }}
                />
                <Bar dataKey="value" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
