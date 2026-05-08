import React from 'react';
import AuditLog from '../components/AuditLog';
import { ClipboardList } from 'lucide-react';

const AuditPage: React.FC = () => {
  return (
    <div className="audit-page">
      <div className="page-header">
        <h1 className="text-gradient">Аудит</h1>
        <p className="text-secondary">Логирование событий системы и активности ИИ</p>
      </div>

      <div className="serpent-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
          <ClipboardList size={24} className="text-emerald" />
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>События системы</h2>
        </div>
        
        <AuditLog />
      </div>
    </div>
  );
};

export default AuditPage;
