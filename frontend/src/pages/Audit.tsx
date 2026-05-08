import React, { useState } from 'react';
import AuditLog from '../components/AuditLog';
import TaskMonitoring from '../components/TaskMonitoring';
import PrometheusMetrics from '../components/PrometheusMetrics';
import { ClipboardList, Activity, TrendingUp } from 'lucide-react';
import './Audit.css';

const AuditPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'audit' | 'tasks' | 'metrics'>('tasks');

  const tabs = [
    { id: 'tasks', label: 'Мониторинг задач', icon: Activity },
    { id: 'metrics', label: 'Метрики Прометеуса', icon: TrendingUp },
    { id: 'audit', label: 'Логи событий', icon: ClipboardList },
  ];

  return (
    <div className="audit-page">
      <div className="page-header">
        <h1 className="text-gradient">Аудит</h1>
        <p className="text-secondary">Логирование событий системы и активности ИИ</p>
      </div>

      <div className="audit-tabs-container">
        <div className="audit-tabs">
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={`audit-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id as 'audit' | 'tasks' | 'metrics')}
              >
                <Icon size={18} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="audit-content serpent-card" style={{ padding: '24px' }}>
        {activeTab === 'tasks' && (
          <div className="audit-tab-content">
            <TaskMonitoring />
          </div>
        )}
        {activeTab === 'metrics' && (
          <div className="audit-tab-content">
            <PrometheusMetrics />
          </div>
        )}
        {activeTab === 'audit' && (
          <div className="audit-tab-content">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
              <ClipboardList size={24} className="text-emerald" />
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>События системы</h2>
            </div>
            <AuditLog />
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditPage;
