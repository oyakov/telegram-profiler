import React, { useState, useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import useSWR from 'swr';
import {
  User,
  Folder,
  LogOut,
  ChevronRight,
  Phone,
  Key,
  Lock,
  Loader2
} from 'lucide-react';
import api from '../services/api';
import './TopBar.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const TopBar: React.FC = () => {
  const [profileOpen, setProfileOpen] = useState(false);
  const [showSavedPhones, setShowSavedPhones] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Telegram Auth State
  const [telegramPhone, setTelegramPhone] = useState('');
  const [telegramCode, setTelegramCode] = useState('');
  const [telegramPassword, setTelegramPassword] = useState('');
  const [telegramStep, setTelegramStep] = useState<'phone' | 'code' | 'password'>('phone');
  const [telegramPhoneHash, setTelegramPhoneHash] = useState('');
  const [telegramLoading, setTelegramLoading] = useState(false);
  const [savedPhones, setSavedPhones] = useState<string[]>([]);
  
  const { data: telegramStatus, mutate: mutateStatus } = useSWR('/api/telegram/auth/status', fetcher, { refreshInterval: 5000 });
  const { data: telegramUser } = useSWR(telegramStatus?.authorized ? '/api/telegram/user' : null, fetcher);

  // Load saved phones from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('saved_telegram_phones');
    if (saved) {
      try {
        setSavedPhones(JSON.parse(saved));
      } catch (e) {
        // Ignore parse errors
      }
    }
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
        setShowSavedPhones(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const savePhoneToHistory = (phone: string) => {
    const updated = [phone, ...savedPhones.filter(p => p !== phone)].slice(0, 5);
    setSavedPhones(updated);
    localStorage.setItem('saved_telegram_phones', JSON.stringify(updated));
  };

  const selectSavedPhone = (phone: string) => {
    setTelegramPhone(phone);
    setShowSavedPhones(false);
  };

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      const res = await api.post('/api/telegram/auth/send_code', { phone: telegramPhone });
      setTelegramPhoneHash(res.data.phone_code_hash);
      savePhoneToHistory(telegramPhone);
      setTelegramStep('code');
      setShowSavedPhones(false);
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
        await mutateStatus();
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
      await api.post('/api/telegram/auth/2fa', {
        phone: telegramPhone,
        phone_code_hash: telegramPhoneHash,
        password: telegramPassword
      });
      await mutateStatus();
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
    if (!window.confirm('Disconnect Telegram?')) return;
    setTelegramLoading(true);
    try {
      await api.post('/api/telegram/auth/logout');
      await mutateStatus();
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

  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <NavLink to="/" className="top-nav-link">
          <User size={18} />
          <span>Профиль</span>
        </NavLink>
        <NavLink to="/tracking" className="top-nav-link">
          <Folder size={18} />
          <span>Папки</span>
        </NavLink>
      </div>

      <div className="header-right">
        {telegramStatus?.authorized && (
          <div className="telegram-status-chip" title="Telegram connected">
            <div className="status-dot online"></div>
            <span>Telegram</span>
          </div>
        )}
        
        <div className="system-status">
          <div className="status-dot online"></div>
          <span>System Online</span>
        </div>

        <div className="profile-container" ref={dropdownRef}>
          <button 
            className={`profile-trigger ${profileOpen ? 'active' : ''}`}
            onClick={() => setProfileOpen(!profileOpen)}
          >
            <div className="avatar-wrapper">
              {telegramUser?.photo_url ? (
                <img src={telegramUser.photo_url} alt="Profile" className="avatar-img" />
              ) : (
                <div className="avatar-placeholder">{telegramUser?.first_name?.[0] || 'O'}</div>
              )}
            </div>
          </button>

          {profileOpen && (
            <div className="profile-dropdown serpent-card">
              <div className="dropdown-header">
                <h3>Аккаунт</h3>
                <p>{telegramStatus?.authorized ? 'Telegram подключен' : 'Требуется авторизация'}</p>
              </div>

              <div className="dropdown-content">
                {telegramStatus?.authorized ? (
                  <div className="user-info-section">
                    <div className="user-details">
                      <div className="user-name">
                        {telegramUser?.first_name} {telegramUser?.last_name}
                      </div>
                      <div className="user-phone">{telegramUser?.phone}</div>
                    </div>
                    <button className="disconnect-btn" onClick={handleDisconnect} disabled={telegramLoading}>
                      <LogOut size={16} />
                      <span>Отключить</span>
                    </button>
                  </div>
                ) : (
                  <div className="auth-form-section">
                    <form onSubmit={
                      telegramStep === 'phone' ? handleSendCode :
                      telegramStep === 'code' ? handleVerifyCode :
                      handleVerify2FA
                    }>
                      {telegramStep === 'phone' && (
                        <div className="auth-input-group">
                          <label><Phone size={14} /> Номер телефона</label>
                          <div style={{ position: 'relative' }}>
                            <input
                              type="tel"
                              placeholder="+7..."
                              value={telegramPhone}
                              onChange={e => setTelegramPhone(e.target.value)}
                              onFocus={() => setShowSavedPhones(true)}
                              autoFocus
                            />
                            {showSavedPhones && savedPhones.length > 0 && (
                              <div style={{
                                position: 'absolute',
                                top: '100%',
                                left: 0,
                                right: 0,
                                background: 'rgba(15, 23, 42, 0.95)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                borderRadius: '8px',
                                marginTop: '4px',
                                zIndex: 1000,
                                maxHeight: '200px',
                                overflowY: 'auto'
                              }}>
                                {savedPhones.map((phone, idx) => (
                                  <button
                                    key={idx}
                                    type="button"
                                    onClick={() => selectSavedPhone(phone)}
                                    style={{
                                      display: 'block',
                                      width: '100%',
                                      padding: '8px 12px',
                                      textAlign: 'left',
                                      background: 'transparent',
                                      border: 'none',
                                      color: '#cbd5e1',
                                      cursor: 'pointer',
                                      borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                                      fontSize: '0.9rem'
                                    }}
                                    onMouseEnter={(e) => {
                                      (e.target as HTMLElement).style.background = 'rgba(16, 185, 129, 0.1)';
                                    }}
                                    onMouseLeave={(e) => {
                                      (e.target as HTMLElement).style.background = 'transparent';
                                    }}
                                  >
                                    {phone}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      {telegramStep === 'code' && (
                        <div className="auth-input-group">
                          <label><Key size={14} /> Код подтверждения</label>
                          <input 
                            type="text" 
                            placeholder="12345" 
                            value={telegramCode}
                            onChange={e => setTelegramCode(e.target.value)}
                            autoFocus
                          />
                        </div>
                      )}
                      {telegramStep === 'password' && (
                        <div className="auth-input-group">
                          <label><Lock size={14} /> 2FA Пароль</label>
                          <input 
                            type="password" 
                            placeholder="Пароль" 
                            value={telegramPassword}
                            onChange={e => setTelegramPassword(e.target.value)}
                            autoFocus
                          />
                        </div>
                      )}
                      
                      <button type="submit" className="auth-submit-btn" disabled={telegramLoading}>
                        <Loader2 size={16} className={telegramLoading ? "spin" : ""} style={{opacity: telegramLoading ? 1 : 0}} />
                        <span>{telegramLoading ? 'Проверяется...' : 'Продолжить'}</span>
                        <ChevronRight size={16} style={{opacity: telegramLoading ? 0 : 1}} />
                      </button>
                    </form>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default TopBar;
