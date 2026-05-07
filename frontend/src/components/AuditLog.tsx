import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { CheckCircle2, AlertCircle, Cpu, Clock, Terminal } from 'lucide-react';
import './AuditLog.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface AuditEntry {
  id: string;
  type: string;
  model: string;
  success: boolean;
  time_ms: number;
  created_at: string;
  details: string;
}

const AuditLog: React.FC = () => {
  const { data, error } = useSWR('/api/stats/audit-logs', fetcher, { refreshInterval: 5000 });

  if (error) return <div className="audit-error">Failed to load logs</div>;
  if (!data) return <div className="audit-loading">Initializing logs...</div>;

  return (
    <div className="audit-log-container serpent-card">
      <div className="audit-header">
        <Terminal size={18} className="text-accent" />
        <h3>Аудит событий ИИ</h3>
      </div>
      <div className="audit-list">
        {data.logs.map((log: AuditEntry) => (
          <div key={log.id} className={`audit-item ${log.success ? 'success' : 'error'}`}>
            <div className="audit-icon">
              {log.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            </div>
            <div className="audit-content">
              <div className="audit-main">
                <span className="audit-type">{log.type}</span>
                <span className="audit-details">{log.details}</span>
              </div>
              <div className="audit-meta">
                <span className="audit-model"><Cpu size={12} /> {log.model}</span>
                <span className="audit-time"><Clock size={12} /> {log.time_ms}ms</span>
                <span className="audit-date">{new Date(log.created_at).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        ))}
        {data.logs.length === 0 && <div className="text-secondary text-center py-4">Нет недавних событий</div>}
      </div>
    </div>
  );
};

export default AuditLog;
