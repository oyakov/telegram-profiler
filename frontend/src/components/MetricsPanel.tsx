import React from 'react';
import { AlertCircle, CheckCircle, TrendingUp, Database, Activity, BarChart3, AlertTriangle } from 'lucide-react';
import '../styles/MetricsPanel.css';

interface MetricCard {
  title: string;
  value: string | number;
  unit?: string;
  icon: React.ReactNode;
  color: 'green' | 'yellow' | 'red' | 'blue';
  trend?: string;
}

interface MetricsPanelProps {
  title: string;
  metrics: MetricCard[];
  alerts?: Array<{ type: string; severity: string; message: string }>;
}

export const MetricCard: React.FC<MetricCard> = ({ title, value, unit, icon, color, trend }) => {
  const colorClass = `metric-card-${color}`;
  return (
    <div className={`metric-card ${colorClass}`}>
      <div className="metric-header">
        <div className="metric-icon">{icon}</div>
        <span className="metric-title">{title}</span>
      </div>
      <div className="metric-value">
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      {trend && <div className="metric-trend">{trend}</div>}
    </div>
  );
};

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ title, metrics, alerts }) => {
  return (
    <div className="metrics-panel">
      <div className="metrics-header">
        <h2>{title}</h2>
        {alerts && alerts.length > 0 && (
          <div className="alert-badge">
            <AlertCircle size={16} />
            {alerts.length} alert{alerts.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      <div className="metrics-grid">
        {metrics.map((metric, idx) => (
          <MetricCard key={idx} {...metric} />
        ))}
      </div>

      {alerts && alerts.length > 0 && (
        <div className="alerts-section">
          <h3>Active Alerts</h3>
          {alerts.map((alert, idx) => (
            <div key={idx} className={`alert alert-${alert.severity}`}>
              {alert.severity === 'high' ? (
                <AlertTriangle size={16} />
              ) : (
                <AlertCircle size={16} />
              )}
              <div>
                <div className="alert-type">{alert.type}</div>
                <div className="alert-message">{alert.message}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const DataQualityMetrics: React.FC<any> = ({ data }) => {
  if (!data) return <div className="loading">Loading...</div>;

  return (
    <MetricsPanel
      title="Data Quality"
      metrics={[
        {
          title: 'Completeness Score',
          value: data.completeness_score,
          unit: '%',
          icon: <CheckCircle size={20} />,
          color: data.completeness_score > 90 ? 'green' : 'yellow',
        },
        {
          title: 'Valid Messages',
          value: data.quality_metrics.valid_messages_percent,
          unit: '%',
          icon: <TrendingUp size={20} />,
          color: 'green',
        },
        {
          title: 'Null Fields',
          value: data.quality_metrics.null_fields_percent,
          unit: '%',
          icon: <AlertCircle size={20} />,
          color: data.quality_metrics.null_fields_percent > 10 ? 'red' : 'green',
        },
        {
          title: 'Total Messages',
          value: data.total_messages.toLocaleString(),
          icon: <BarChart3 size={20} />,
          color: 'blue',
        },
      ]}
    />
  );
};

export const SyncHealthMetrics: React.FC<any> = ({ data }) => {
  if (!data) return <div className="loading">Loading...</div>;

  return (
    <MetricsPanel
      title="Sync Health"
      metrics={[
        {
          title: 'Healthy Channels',
          value: data.healthy,
          unit: `/ ${data.total_channels}`,
          icon: <CheckCircle size={20} />,
          color: 'green',
        },
        {
          title: 'Stale Channels',
          value: data.stale,
          icon: <AlertCircle size={20} />,
          color: data.stale > 0 ? 'yellow' : 'green',
        },
        {
          title: 'Critical Channels',
          value: data.critical,
          icon: <AlertTriangle size={20} />,
          color: data.critical > 0 ? 'red' : 'green',
        },
        {
          title: 'Sync Health Score',
          value: data.sync_health_score,
          unit: '%',
          icon: <Activity size={20} />,
          color: data.sync_health_score > 80 ? 'green' : 'yellow',
        },
      ]}
      alerts={data.details?.filter((d: any) => d.status !== 'healthy').map((d: any) => ({
        type: d.status.toUpperCase(),
        severity: d.status === 'critical' ? 'high' : 'medium',
        message: `${d.channel}: ${d.last_sync_hours_ago ? d.last_sync_hours_ago + 'h ago' : 'never synced'}`,
      }))}
    />
  );
};

export const BusinessMetrics: React.FC<any> = ({ data }) => {
  if (!data) return <div className="loading">Loading...</div>;

  return (
    <MetricsPanel
      title="Business Metrics"
      metrics={[
        {
          title: 'Total Leads',
          value: data.lead_quality.total_leads.toLocaleString(),
          icon: <TrendingUp size={20} />,
          color: 'green',
        },
        {
          title: 'Lead Ratio',
          value: data.lead_quality.lead_ratio,
          unit: '%',
          icon: <BarChart3 size={20} />,
          color: 'blue',
        },
        {
          title: 'Extraction Accuracy',
          value: data.extraction_metrics.accuracy,
          unit: '%',
          icon: <CheckCircle size={20} />,
          color: data.extraction_metrics.accuracy > 80 ? 'green' : 'yellow',
        },
        {
          title: 'Monthly Cost Est.',
          value: '$' + data.cost_metrics.monthly_estimate_usd,
          icon: <Database size={20} />,
          color: 'blue',
        },
      ]}
    />
  );
};
