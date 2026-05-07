import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { RefreshCcw, Search, ExternalLink, Plus, Phone } from 'lucide-react';
import './Tracking.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Tracking: React.FC = () => {
  const { data, mutate } = useSWR('/api/tracking/channels', fetcher);
  const { data: syncData, mutate: mutateSyncStatus } = useSWR('/api/connectors/status', fetcher, { refreshInterval: 2000 });
  const [searchTerm, setSearchTerm] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [telegramPhone, setTelegramPhone] = useState('');
  const [telegramCode, setTelegramCode] = useState('');
  const [telegramPassword, setTelegramPassword] = useState('');
  const [telegramStep, setTelegramStep] = useState<'phone' | 'code' | 'password'>('phone');
  const [telegramPhoneHash, setTelegramPhoneHash] = useState('');
  const [telegramLoading, setTelegramLoading] = useState(false);
  const [telegramAuthorized, setTelegramAuthorized] = useState<boolean | null>(null);

  const checkTelegramAuth = async () => {
    try {
      const res = await api.get('/api/telegram/auth/status');
      setTelegramAuthorized(res.data.authorized);
    } catch (err) {
      setTelegramAuthorized(false);
    }
  };

  React.useEffect(() => {
    checkTelegramAuth();
  }, []);

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      const res = await api.post('/api/telegram/auth/send_code', { phone: telegramPhone });
      setTelegramPhoneHash(res.data.phone_code_hash);
      setTelegramStep('code');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Failed to send code'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      const res = await api.post('/api/telegram/auth/verify', {
        phone: telegramPhone,
        code: telegramCode,
        phone_code_hash: telegramPhoneHash,
      });
      if (res.data.status === 'requires_2fa') {
        setTelegramStep('password');
      } else {
        setTelegramAuthorized(true);
        setTelegramPhone('');
        setTelegramCode('');
      }
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Verification failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      await api.post('/api/telegram/auth/2fa', { password: telegramPassword });
      setTelegramAuthorized(true);
      setTelegramPhone('');
      setTelegramCode('');
      setTelegramPassword('');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || '2FA failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect Telegram? You can login again anytime.')) return;
    setTelegramLoading(true);
    try {
      await api.post('/api/telegram/auth/logout');
      setTelegramAuthorized(false);
      setTelegramStep('phone');
      setTelegramPhone('');
      setTelegramCode('');
      setTelegramPassword('');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Logout failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await api.post('/api/connectors/telegram/sync');
      alert('Синхронизация запущена в фоновом режиме');
      mutate();
      mutateSyncStatus();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSyncing(false);
    }
  };

  const filteredChannels = data?.channels?.filter((ch: any) => 
    ch.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
    ch.username?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  return (
    <div className="tracking-page">
      {/* Telegram Auth Card */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 78, 59, 0.1))',
        border: '1px solid rgba(16, 185, 129, 0.2)',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '24px',
        maxWidth: '450px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <Phone size={24} style={{ color: '#10b981' }} />
          <h3 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Telegram Auth</h3>
        </div>

        {telegramAuthorized === true ? (
          <div style={{ padding: '16px 0' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '16px',
              padding: '12px',
              background: 'rgba(16, 185, 129, 0.1)',
              borderRadius: '8px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '20px' }}>✅</span>
                <div>
                  <p style={{ color: '#10b981', margin: '0', fontWeight: 'bold' }}>Connected</p>
                  <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: '12px' }}>Session active</p>
                </div>
              </div>
              <button
                onClick={handleDisconnect}
                disabled={telegramLoading}
                style={{
                  padding: '6px 12px',
                  background: 'rgba(239, 68, 68, 0.1)',
                  color: '#fca5a5',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '4px',
                  cursor: telegramLoading ? 'not-allowed' : 'pointer',
                  fontSize: '12px',
                  fontWeight: 'bold'
                }}
              >
                {telegramLoading ? 'Processing...' : 'Disconnect'}
              </button>
            </div>
          </div>
        ) : telegramAuthorized === null ? (
          <div style={{ color: '#cbd5e1', textAlign: 'center', padding: '20px' }}>
            Checking...
          </div>
        ) : (
          <form onSubmit={
            telegramStep === 'phone' ? handleSendCode :
            telegramStep === 'code' ? handleVerifyCode :
            handleVerify2FA
          } style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{
              background: 'rgba(30, 41, 59, 0.3)',
              border: '1px solid rgba(148, 163, 184, 0.15)',
              borderRadius: '8px',
              padding: '12px'
            }}>
              {telegramStep === 'phone' && (
                <>
                  <label style={{ color: '#94a3b8', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Step 1: Phone Number</label>
                  <input
                    type="tel"
                    placeholder="+38123456789"
                    value={telegramPhone}
                    onChange={(e) => setTelegramPhone(e.target.value)}
                    disabled={telegramLoading}
                    autoFocus
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      marginTop: '8px',
                      background: 'rgba(15, 23, 42, 0.6)',
                      border: '1px solid rgba(16, 185, 129, 0.2)',
                      color: '#f8fafc',
                      borderRadius: '6px',
                      fontSize: '14px',
                      boxSizing: 'border-box'
                    }}
                  />
                  <p style={{ color: '#64748b', fontSize: '12px', margin: '8px 0 0', marginBottom: 0 }}>You'll receive a code in Telegram</p>
                </>
              )}
              {telegramStep === 'code' && (
                <>
                  <label style={{ color: '#94a3b8', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Step 2: Verification Code</label>
                  <input
                    type="text"
                    placeholder="123456"
                    value={telegramCode}
                    onChange={(e) => setTelegramCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    disabled={telegramLoading}
                    autoFocus
                    maxLength={6}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      marginTop: '8px',
                      background: 'rgba(15, 23, 42, 0.6)',
                      border: '1px solid rgba(16, 185, 129, 0.2)',
                      color: '#f8fafc',
                      borderRadius: '6px',
                      fontSize: '14px',
                      boxSizing: 'border-box',
                      letterSpacing: '4px'
                    }}
                  />
                  <p style={{ color: '#64748b', fontSize: '12px', margin: '8px 0 0', marginBottom: 0 }}>Check your Telegram app for the code</p>
                </>
              )}
              {telegramStep === 'password' && (
                <>
                  <label style={{ color: '#94a3b8', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Step 3: Two-Factor Password</label>
                  <input
                    type="password"
                    placeholder="Your password"
                    value={telegramPassword}
                    onChange={(e) => setTelegramPassword(e.target.value)}
                    disabled={telegramLoading}
                    autoFocus
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      marginTop: '8px',
                      background: 'rgba(15, 23, 42, 0.6)',
                      border: '1px solid rgba(16, 185, 129, 0.2)',
                      color: '#f8fafc',
                      borderRadius: '6px',
                      fontSize: '14px',
                      boxSizing: 'border-box'
                    }}
                  />
                  <p style={{ color: '#64748b', fontSize: '12px', margin: '8px 0 0', marginBottom: 0 }}>Your account requires 2-factor authentication</p>
                </>
              )}
            </div>
            <button
              type="submit"
              disabled={telegramLoading}
              style={{
                padding: '11px 16px',
                background: telegramLoading ? 'rgba(16, 185, 129, 0.5)' : 'linear-gradient(135deg, #10b981, #059669)',
                color: '#f8fafc',
                border: 'none',
                borderRadius: '6px',
                fontWeight: '600',
                cursor: telegramLoading ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                transition: 'all 0.2s',
                boxShadow: telegramLoading ? 'none' : '0 4px 12px rgba(16, 185, 129, 0.2)'
              }}
            >
              {telegramLoading ? '⏳ Processing...' : `Continue → ${telegramStep === 'phone' ? 'Send Code' : telegramStep === 'code' ? 'Verify Code' : 'Verify 2FA'}`}
            </button>
          </form>
        )}
      </div>

      {/* Sync Status Card */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.1))',
        border: '1px solid rgba(59, 130, 246, 0.2)',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '24px',
        maxWidth: '450px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <RefreshCcw size={24} style={{ color: '#3b82f6' }} />
          <h3 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Статус Синхронизации</h3>
        </div>

        {syncData?.connectors ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {syncData.connectors.map((connector: any) => {
              const isRunning = connector.status === 'running';
              const hasError = connector.status === 'error';
              const messagesCount = connector.messages_fetched || 0;

              return (
                <div key={connector.connector} style={{
                  padding: '16px',
                  background: isRunning ? 'rgba(59, 130, 246, 0.1)' : hasError ? 'rgba(239, 68, 68, 0.1)' : 'rgba(148, 163, 184, 0.05)',
                  border: `1px solid ${isRunning ? 'rgba(59, 130, 246, 0.3)' : hasError ? 'rgba(239, 68, 68, 0.3)' : 'rgba(148, 163, 184, 0.15)'}`,
                  borderRadius: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <p style={{ color: '#f8fafc', margin: '0', fontWeight: '600', textTransform: 'capitalize' }}>{connector.connector}</p>
                    <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: '12px' }}>
                      {isRunning ? '⏳ Синхронизация...' : hasError ? '❌ Ошибка' : '✓ Готово'}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ color: '#3b82f6', margin: '0', fontWeight: '600' }}>{messagesCount.toLocaleString()}</p>
                    <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: '12px' }}>сообщений</p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: '#cbd5e1', textAlign: 'center', padding: '20px' }}>
            Загрузка статуса...
          </div>
        )}
      </div>

      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">Управление Отслеживанием</h1>
          <p className="text-secondary">Мониторинг Telegram каналов и групп</p>
        </div>
        <div className="actions">
          <button className="btn-venom secondary" onClick={handleSync} disabled={isSyncing}>
            <RefreshCcw size={18} className={isSyncing ? 'spin' : ''} />
            Синхронизировать
          </button>
          <button className="btn-venom primary">
            <Plus size={18} />
            Добавить канал
          </button>
        </div>
      </div>

      <div className="search-bar-container serpent-card">
        <Search size={20} className="text-secondary" />
        <input 
          type="text" 
          placeholder="Поиск по каналам..." 
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="channels-grid">
        {filteredChannels.map((ch: any) => (
          <div key={ch.id} className="channel-card serpent-card">
            <div className="channel-header">
              <div className="channel-info">
                <h4>{ch.title}</h4>
                <span className="username">@{ch.username || 'private'}</span>
              </div>
              <div className={`status-badge ${ch.is_active ? 'active' : 'idle'}`}>
                {ch.is_active ? 'Active' : 'Idle'}
              </div>
            </div>
            
            <div className="channel-stats">
              <div className="stat">
                <span className="label">Сообщений</span>
                <span className="value">{ch.messages_count.toLocaleString()}</span>
              </div>
              <div className="stat">
                <span className="label">Тип</span>
                <span className="value">{ch.type}</span>
              </div>
            </div>

            <div className="channel-footer">
              <span className="last-sync">Sync: {new Date(ch.last_sync).toLocaleDateString()}</span>
              <a href={`https://t.me/${ch.username}`} target="_blank" rel="noreferrer" className="view-link">
                <ExternalLink size={14} />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Tracking;
