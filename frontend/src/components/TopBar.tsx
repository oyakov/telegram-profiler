import React, { useState, useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import useSWR from 'swr';
import { User, Folder, LogOut, ChevronRight, Phone, Key, Lock, Loader2 } from 'lucide-react';
import api, { fetcher } from '../services/api';
import { useTelegramAuth } from '../hooks/useTelegramAuth';
import { useToast } from '../context/ToastContext';
import { useConfirm } from '../context/ConfirmContext';
import './TopBar.css';

const TopBar: React.FC = () => {
  const [profileOpen, setProfileOpen] = useState(false);
  const [showSavedPhones, setShowSavedPhones] = useState(false);
  const [savedPhones, setSavedPhones] = useState<string[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { showToast } = useToast();
  const { confirm } = useConfirm();

  const { data: telegramStatus, mutate: mutateStatus, error: statusError } = useSWR(
    '/api/telegram/auth/status', fetcher, { refreshInterval: 30000 }
  );
  const telegramUser = telegramStatus?.profile;
  const selectedDb = localStorage.getItem('selected_db') || 'crm';
  const avatarUrl = telegramUser?.telegram_id
    ? `/api/telegram/media/avatar/${telegramUser.telegram_id}?db=${selectedDb}`
    : null;

  const isSystemOnline = !statusError;

  const auth = useTelegramAuth({
    onSuccess: async () => {
      await mutateStatus();
      setShowSavedPhones(false);
    },
  });

  useEffect(() => {
    try {
      const saved = localStorage.getItem('saved_telegram_phones');
      if (saved) setSavedPhones(JSON.parse(saved));
    } catch {}
  }, []);

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

  const handlePhoneSubmit = async (e: React.FormEvent) => {
    savePhoneToHistory(auth.phone);
    await auth.sendCode(e);
  };

  const handleDisconnect = async () => {
    if (!await confirm('Отключить Telegram аккаунт от системы?', 'Отключение')) return;
    try {
      await api.post('/api/telegram/auth/logout');
      await mutateStatus();
      auth.reset();
      showToast('success', 'Telegram успешно отключён');
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось отключиться');
    }
  };

  const avatarInitial = telegramUser?.first_name?.[0]?.toUpperCase() ?? '?';


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
          <div className="telegram-status-chip" title="Telegram подключён">
            <div className="status-dot online" />
            <span>Telegram</span>
          </div>
        )}

        <div className="system-status">
          <div className={`status-dot ${isSystemOnline ? 'online' : 'offline'}`} />
          <span>{isSystemOnline ? 'Система онлайн' : 'Система недоступна'}</span>
        </div>

        <div className="profile-container" ref={dropdownRef}>
          <button
            className={`profile-trigger ${profileOpen ? 'active' : ''}`}
            onClick={() => setProfileOpen(!profileOpen)}
            aria-label="Меню профиля"
          >
            <div className="avatar-wrapper">
              {avatarUrl ? (
                <img src={avatarUrl} alt="Профиль" className="avatar-img"
                  onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
              ) : (
                <div className="avatar-placeholder">{avatarInitial}</div>
              )}
            </div>
          </button>

          {profileOpen && (
            <div className="profile-dropdown serpent-card">
              <div className="dropdown-header">
                <h3>Аккаунт</h3>
                <p>{telegramStatus?.authorized ? 'Telegram подключён' : 'Требуется авторизация'}</p>
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
                    <button
                      className="disconnect-btn"
                      onClick={handleDisconnect}
                      disabled={auth.loading}
                    >
                      <LogOut size={16} />
                      <span>Отключить</span>
                    </button>
                  </div>
                ) : (
                  <div className="auth-form-section">
                    {auth.error && <div className="auth-error">{auth.error}</div>}
                    <form onSubmit={
                      auth.step === 'phone' ? handlePhoneSubmit :
                      auth.step === 'code'  ? auth.verifyCode  :
                      auth.verify2FA
                    }>
                      {auth.step === 'phone' && (
                        <div className="auth-input-group">
                          <label><Phone size={14} /> Номер телефона</label>
                          <div className="phone-input-wrapper">
                            <input
                              type="tel"
                              placeholder="+7..."
                              value={auth.phone}
                              onChange={e => auth.setPhone(e.target.value)}
                              onFocus={() => setShowSavedPhones(true)}
                              autoFocus
                            />
                            {showSavedPhones && savedPhones.length > 0 && (
                              <div className="saved-phones-dropdown">
                                {savedPhones.map((p, idx) => (
                                  <button
                                    key={idx}
                                    type="button"
                                    className="saved-phone-item"
                                    onClick={() => {
                                      auth.setPhone(p);
                                      setShowSavedPhones(false);
                                    }}
                                  >
                                    {p}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      {auth.step === 'code' && (
                        <div className="auth-input-group">
                          <label><Key size={14} /> Код подтверждения</label>
                          <input
                            type="text"
                            placeholder="12345"
                            value={auth.code}
                            onChange={e => auth.setCode(e.target.value)}
                            autoFocus
                          />
                        </div>
                      )}
                      {auth.step === '2fa' && (
                        <div className="auth-input-group">
                          <label><Lock size={14} /> 2FA Пароль</label>
                          <input
                            type="password"
                            placeholder="Пароль"
                            value={auth.twoFa}
                            onChange={e => auth.setTwoFa(e.target.value)}
                            autoFocus
                          />
                        </div>
                      )}

                      <button type="submit" className="auth-submit-btn" disabled={auth.loading}>
                        <Loader2
                          size={16}
                          className={auth.loading ? 'spin' : ''}
                          style={{ opacity: auth.loading ? 1 : 0 }}
                        />
                        <span>{auth.loading ? 'Проверка...' : 'Продолжить'}</span>
                        <ChevronRight size={16} style={{ opacity: auth.loading ? 0 : 1 }} />
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
