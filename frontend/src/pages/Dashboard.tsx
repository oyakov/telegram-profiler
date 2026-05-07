import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { Users, MessageSquare, Radio, Mic } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area 
} from 'recharts';
import './Dashboard.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

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

  const pieData = [
    { name: 'Contacts', value: stats.total_contacts || 0 },
    { name: 'Leads', value: stats.total_leads || 0 },
  ];

  const COLORS = ['#10b981', '#064e3b', '#f59e0b', '#065f46'];

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1 className="text-gradient">Обзор Проекта</h1>
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

        <div className="chart-container glass">
          <h3>📈 Распределение аудитории</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={pieData}
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                   contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
