import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { TrendingUp, HardDrive, Cpu, AlertCircle } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './PrometheusMetrics.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface MetricPoint {
  timestamp: number;
  value: number;
}

const PrometheusMetrics: React.FC = () => {
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h'>('1h');
  const { data: metricsData, error: metricsError } = useSWR(
    `/api/stats/prometheus?range=${timeRange}`,
    fetcher,
    { refreshInterval: 30000, revalidateOnFocus: false }
  );

  const formatMetricsForChart = (data: MetricPoint[] | undefined) => {
    if (!data || !Array.isArray(data)) return [];
    return data.map(point => ({
      time: new Date(point.timestamp).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      value: point.value
    })).slice(-20); // Last 20 points
  };

  if (metricsError) {
    return (
      <div className="prometheus-error">
        <AlertCircle size={24} />
        <p>Failed to load Prometheus metrics</p>
        <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '8px' }}>
          Make sure Prometheus is running and accessible
        </p>
      </div>
    );
  }

  if (!metricsData) {
    return <div className="prometheus-loading">Loading Prometheus metrics...</div>;
  }

  const cpuData = formatMetricsForChart(metricsData.cpu_usage);
  const memoryData = formatMetricsForChart(metricsData.memory_usage);
  const latencyData = formatMetricsForChart(metricsData.request_latency);
  const errorRateData = formatMetricsForChart(metricsData.error_rate);

  const getCurrentValue = (data: MetricPoint[] | undefined) => {
    if (!data || data.length === 0) return '—';
    return data[data.length - 1].value.toFixed(2);
  };

  const cpuCurrent = getCurrentValue(metricsData.cpu_usage);
  const memoryCurrent = getCurrentValue(metricsData.memory_usage);
  const latencyCurrent = getCurrentValue(metricsData.request_latency);
  const errorRateCurrent = getCurrentValue(metricsData.error_rate);

  return (
    <div className="prometheus-metrics-container">
      <div className="metrics-controls">
        <div className="time-range-selector">
          <button
            className={`range-btn ${timeRange === '1h' ? 'active' : ''}`}
            onClick={() => setTimeRange('1h')}
          >
            1ч
          </button>
          <button
            className={`range-btn ${timeRange === '6h' ? 'active' : ''}`}
            onClick={() => setTimeRange('6h')}
          >
            6ч
          </button>
          <button
            className={`range-btn ${timeRange === '24h' ? 'active' : ''}`}
            onClick={() => setTimeRange('24h')}
          >
            24ч
          </button>
        </div>
      </div>

      <div className="metrics-summary-grid">
        <div className="metric-summary serpent-card">
          <div className="summary-icon cpu">
            <Cpu size={24} />
          </div>
          <div className="summary-content">
            <div className="summary-label">CPU использование</div>
            <div className="summary-value">{cpuCurrent}%</div>
          </div>
        </div>

        <div className="metric-summary serpent-card">
          <div className="summary-icon memory">
            <HardDrive size={24} />
          </div>
          <div className="summary-content">
            <div className="summary-label">Память</div>
            <div className="summary-value">{memoryCurrent} MB</div>
          </div>
        </div>

        <div className="metric-summary serpent-card">
          <div className="summary-icon latency">
            <TrendingUp size={24} />
          </div>
          <div className="summary-content">
            <div className="summary-label">Задержка запроса</div>
            <div className="summary-value">{latencyCurrent}ms</div>
          </div>
        </div>

        <div className="metric-summary serpent-card">
          <div className="summary-icon errors">
            <AlertCircle size={24} />
          </div>
          <div className="summary-content">
            <div className="summary-label">Частота ошибок</div>
            <div className="summary-value">{errorRateCurrent}%</div>
          </div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="metric-chart serpent-card">
          <h4>CPU использование</h4>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={cpuData}>
              <defs>
                <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid #3b82f6' }} />
              <Area type="monotone" dataKey="value" stroke="#3b82f6" fillOpacity={1} fill="url(#colorCpu)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="metric-chart serpent-card">
          <h4>Память</h4>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={memoryData}>
              <defs>
                <linearGradient id="colorMemory" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid #a855f7' }} />
              <Area type="monotone" dataKey="value" stroke="#a855f7" fillOpacity={1} fill="url(#colorMemory)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="metric-chart serpent-card full-width">
          <h4>Задержка запроса</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={latencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid #f59e0b' }} />
              <Line type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="metric-chart serpent-card full-width">
          <h4>Частота ошибок</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={errorRateData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid #ef4444' }} />
              <Line type="monotone" dataKey="value" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default PrometheusMetrics;
