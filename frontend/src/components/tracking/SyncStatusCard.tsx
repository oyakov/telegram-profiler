import React from 'react';
import { RefreshCcw } from 'lucide-react';

interface SyncStatusCardProps {
  syncData: any;
  channelsCount: number;
  totalMessages: number;
}

const SyncStatusCard: React.FC<SyncStatusCardProps> = ({ syncData, channelsCount, totalMessages }) => {
  return (
    <div style={{ marginBottom: '24px' }}>
      <div style={{
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.1))',
        border: '1px solid rgba(59, 130, 246, 0.2)',
        borderRadius: '12px',
        padding: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <RefreshCcw size={20} style={{ color: '#3b82f6' }} />
          <h3 style={{ color: '#f8fafc', margin: 0, fontSize: '16px' }}>Статус Синхронизации</h3>
        </div>

        {syncData?.connectors ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Overall Statistics */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '10px',
              padding: '12px',
              background: 'rgba(148, 163, 184, 0.05)',
              borderRadius: '8px'
            }}>
              <div>
                <p style={{ color: '#64748b', margin: 0, fontSize: '11px' }}>Каналы</p>
                <p style={{ color: '#3b82f6', margin: '4px 0 0', fontSize: '16px', fontWeight: '600' }}>{channelsCount}</p>
              </div>
              <div>
                <p style={{ color: '#64748b', margin: 0, fontSize: '11px' }}>Сообщений</p>
                <p style={{ color: '#10b981', margin: '4px 0 0', fontSize: '16px', fontWeight: '600' }}>{totalMessages.toLocaleString()}</p>
              </div>
            </div>

            {/* Connector Status */}
            {syncData.connectors.map((connector: any) => {
              const isRunning = connector.status === 'running';
              const hasError = connector.status === 'error';

              return (
                <div key={connector.connector} style={{
                  padding: '12px',
                  background: isRunning ? 'rgba(59, 130, 246, 0.1)' : hasError ? 'rgba(239, 68, 68, 0.1)' : 'rgba(148, 163, 184, 0.05)',
                  border: `1px solid ${isRunning ? 'rgba(59, 130, 246, 0.3)' : hasError ? 'rgba(239, 68, 68, 0.3)' : 'rgba(148, 163, 184, 0.15)'}`,
                  borderRadius: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <p style={{ color: '#f8fafc', margin: '0', fontWeight: '600', textTransform: 'capitalize', fontSize: '14px' }}>{connector.connector}</p>
                    <p style={{ color: '#64748b', margin: '2px 0 0', fontSize: '11px' }}>
                      {isRunning ? '⏳ Загружается...' : hasError ? '❌ Ошибка' : '✓ Готово'}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: '#cbd5e1', textAlign: 'center', padding: '16px', fontSize: '13px' }}>
            Загрузка...
          </div>
        )}
      </div>
    </div>
  );
};

export default SyncStatusCard;
