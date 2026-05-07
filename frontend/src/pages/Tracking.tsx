import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { RefreshCcw, Search, ExternalLink, Plus, Phone } from 'lucide-react';
import './Tracking.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Tracking: React.FC = () => {
  const { data, mutate } = useSWR('/api/tracking/channels', fetcher);
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

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await api.post('/api/connectors/telegram/sync');
      alert('Синхронизация запущена в фоновом режиме');
      mutate();
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
          <div style={{ color: '#10b981', textAlign: 'center', padding: '20px' }}>
            <div style={{ fontSize: '32px', marginBottom: '10px' }}>✅</div>
            <p style={{ margin: 0 }}>Telegram Connected</p>
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
          } style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {telegramStep === 'phone' && (
              <>
                <label style={{ color: '#cbd5e1', fontSize: '14px' }}>Phone Number</label>
                <input
                  type="tel"
                  placeholder="+38..."
                  value={telegramPhone}
                  onChange={(e) => setTelegramPhone(e.target.value)}
                  disabled={telegramLoading}
                  style={{
                    padding: '10px 12px',
                    background: 'rgba(30, 41, 59, 0.5)',
                    border: '1px solid rgba(148, 163, 184, 0.2)',
                    color: '#f8fafc',
                    borderRadius: '6px'
                  }}
                />
              </>
            )}
            {telegramStep === 'code' && (
              <>
                <label style={{ color: '#cbd5e1', fontSize: '14px' }}>Verification Code</label>
                <input
                  type="text"
                  placeholder="Code from Telegram"
                  value={telegramCode}
                  onChange={(e) => setTelegramCode(e.target.value)}
                  disabled={telegramLoading}
                  style={{
                    padding: '10px 12px',
                    background: 'rgba(30, 41, 59, 0.5)',
                    border: '1px solid rgba(148, 163, 184, 0.2)',
                    color: '#f8fafc',
                    borderRadius: '6px'
                  }}
                />
              </>
            )}
            {telegramStep === 'password' && (
              <>
                <label style={{ color: '#cbd5e1', fontSize: '14px' }}>2FA Password</label>
                <input
                  type="password"
                  placeholder="Your 2FA password"
                  value={telegramPassword}
                  onChange={(e) => setTelegramPassword(e.target.value)}
                  disabled={telegramLoading}
                  style={{
                    padding: '10px 12px',
                    background: 'rgba(30, 41, 59, 0.5)',
                    border: '1px solid rgba(148, 163, 184, 0.2)',
                    color: '#f8fafc',
                    borderRadius: '6px'
                  }}
                />
              </>
            )}
            <button
              type="submit"
              disabled={telegramLoading}
              style={{
                padding: '10px 16px',
                background: 'linear-gradient(135deg, #10b981, #059669)',
                color: '#f8fafc',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 'bold',
                cursor: telegramLoading ? 'not-allowed' : 'pointer',
                opacity: telegramLoading ? 0.6 : 1
              }}
            >
              {telegramLoading ? 'Processing...' : 'Continue'}
            </button>
          </form>
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
